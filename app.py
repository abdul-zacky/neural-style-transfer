from flask import Flask, request, render_template, send_from_directory, url_for, jsonify
import os
import uuid
import threading
import time
import glob
import random
import ssl
import json
from datetime import datetime

# Temporarily disable SSL verification (NOT recommended for production)
ssl._create_default_https_context = ssl._create_unverified_context

from werkzeug.utils import secure_filename
from model import StyleTransfer

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['OUTPUT_FOLDER'] = 'static/outputs'
app.config['METADATA_FILE'] = 'static/metadata.json'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['MAX_EXAMPLES'] = 6  # Maximum number of examples to show on main page

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize style transfer model
style_transfer = StyleTransfer(image_size=356)

# Store for tracking progress of each job
progress_tracker = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def update_progress(job_id, progress, status):
    """Update progress for a specific job"""
    progress_tracker[job_id] = {
        'progress': progress,
        'status': status,
        'updated_at': time.time()
    }

def load_metadata():
    """Load metadata for previous transfers"""
    if os.path.exists(app.config['METADATA_FILE']):
        try:
            with open(app.config['METADATA_FILE'], 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_metadata(metadata):
    """Save metadata for style transfers"""
    with open(app.config['METADATA_FILE'], 'w') as f:
        json.dump(metadata, f)

def add_transfer_metadata(job_id, content_path, style_path, result_path):
    """Add metadata for a completed style transfer"""
    metadata = load_metadata()
    
    # Create new entry
    new_entry = {
        'id': job_id,
        'content_image': content_path,
        'style_image': style_path,
        'result_image': result_path,
        'timestamp': datetime.now().isoformat()
    }
    
    # Add to beginning of list to show newest first
    metadata.insert(0, new_entry)
    
    # Limit number of entries to prevent unlimited growth
    metadata = metadata[:100]  # Keep only the 100 most recent
    
    # Save updated metadata
    save_metadata(metadata)

def get_recent_transfers(limit=6):
    """Get recent successful style transfers"""
    metadata = load_metadata()
    
    # Filter valid results (all paths exist)
    valid_results = []
    for item in metadata:
        # Check if all files exist
        content_exists = os.path.exists(item['content_image'])
        style_exists = os.path.exists(item['style_image']) 
        result_exists = os.path.exists(item['result_image'])
        
        if content_exists and style_exists and result_exists:
            valid_results.append(item)
            if len(valid_results) >= limit:
                break
    
    return valid_results

@app.route('/')
def home():
    # Get recent transfers to display as examples
    recent_transfers = get_recent_transfers(app.config['MAX_EXAMPLES'])
    return render_template('index.html', recent_transfers=recent_transfers)

@app.route('/progress/<job_id>')
def get_progress(job_id):
    """Get the current progress of a job"""
    if job_id in progress_tracker:
        return jsonify(progress_tracker[job_id])
    return jsonify({'progress': 0, 'status': 'Job not found'})

def process_style_transfer(job_id, content_path, style_path, output_path, steps, alpha, beta):
    """Process style transfer in a background thread"""
    try:
        # Create a callback function to track progress
        def progress_callback(progress, status):
            update_progress(job_id, progress, status)
            
        # Run style transfer with progress tracking
        style_transfer.transfer_style(
            content_path, style_path, output_path, 
            total_steps=steps, alpha=alpha, beta=beta,
            progress_callback=progress_callback
        )
        
        # Save metadata about this transfer
        add_transfer_metadata(job_id, content_path, style_path, output_path)
        
        # Final update - Done
        update_progress(job_id, 100, "Style transfer complete!")
    except Exception as e:
        # Update with error
        update_progress(job_id, -1, f"Error: {str(e)}")

@app.route('/transfer', methods=['POST'])
def transfer_style():
    # Check if both files are present
    if 'content_image' not in request.files or 'style_image' not in request.files:
        return 'No file part', 400
    
    content_file = request.files['content_image']
    style_file = request.files['style_image']
    
    # Check if both files are selected
    if content_file.filename == '' or style_file.filename == '':
        return 'No selected file', 400
    
    # Check if both files are valid
    if not allowed_file(content_file.filename) or not allowed_file(style_file.filename):
        return 'Invalid file type', 400
    
    # Generate unique filenames and job ID
    job_id = str(uuid.uuid4())
    content_filename = secure_filename(f"{job_id}_content_{content_file.filename}")
    style_filename = secure_filename(f"{job_id}_style_{style_file.filename}")
    
    # Save files
    content_path = os.path.join(app.config['UPLOAD_FOLDER'], content_filename)
    style_path = os.path.join(app.config['UPLOAD_FOLDER'], style_filename)
    
    content_file.save(content_path)
    style_file.save(style_path)
    
    # Generate output filename
    output_filename = f"{job_id}.png"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    # Get style transfer parameters
    steps = int(request.form.get('steps', 1000))
    alpha = float(request.form.get('alpha', 1.0))
    beta = float(request.form.get('beta', 0.01))
    
    # Initialize progress tracker
    update_progress(job_id, 0, "Starting style transfer")
    
    # Start processing in a background thread
    thread = threading.Thread(
        target=process_style_transfer,
        args=(job_id, content_path, style_path, output_path, steps, alpha, beta)
    )
    thread.daemon = True
    thread.start()
    
    # Return processing page
    return render_template(
        'processing.html',
        job_id=job_id,
        content_image=content_path,
        style_image=style_path,
        result_image=url_for('static', filename=f'outputs/{output_filename}')
    )

@app.route('/result/<job_id>')
def show_result(job_id):
    """Show result page for a completed job"""
    # Get the paths
    output_filename = f"{job_id}.png"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    # Check if the result exists
    if not os.path.exists(output_path):
        return "Result not found", 404
    
    # Find content and style images used for this job
    content_path = None
    style_path = None
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.startswith(job_id):
            if "_content_" in filename.lower():
                content_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            elif "_style_" in filename.lower():
                style_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Find intermediate images
    intermediate_steps = []
    base_filename = output_path.split('.')[0]
    for filename in os.listdir(app.config['OUTPUT_FOLDER']):
        if filename.startswith(f"{job_id}_") and filename.endswith('.png'):
            # Extract step number
            try:
                step = int(filename.split('_')[-1].split('.')[0])
                intermediate_steps.append(step)
            except ValueError:
                continue
    
    # Sort steps
    intermediate_steps.sort()
    
    # Return result page
    return render_template(
        'result.html',
        content_image=content_path,
        style_image=style_path,
        result_image=url_for('static', filename=f'outputs/{output_filename}'),
        intermediate_steps=intermediate_steps
    )

if __name__ == '__main__':
    app.run(debug=True, threaded=True)