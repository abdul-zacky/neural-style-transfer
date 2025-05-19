# Neural Style Transfer Web Application

This project implements Neural Style Transfer using PyTorch and provides a web interface for users to apply artistic styles to their images.

## Features

- Upload content and style images
- Adjust parameters for style transfer
- View and download results
- Responsive web interface

## Installation

### Local Setup

1. Clone this repository:
```bash
git clone https://github.com/your-username/neural-style-transfer.git
cd neural-style-transfer
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Visit `http://localhost:5000` in your browser

### Using Docker

1. Build the Docker image:
```bash
docker build -t neural-style-transfer .
```

2. Run the container:
```bash
docker run -p 8080:8080 neural-style-transfer
```

3. Visit `http://localhost:8080` in your browser

## Deployment Options

### Heroku

1. Install the Heroku CLI and login
2. Create a new app:
```bash
heroku create your-app-name
git push heroku main
```

### Google Cloud Run

1. Build and push your container:
```bash
gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/neural-style-transfer
```

2. Deploy to Cloud Run:
```bash
gcloud run deploy --image gcr.io/YOUR-PROJECT-ID/neural-style-transfer --platform managed
```

### AWS Elastic Beanstalk

1. Install the EB CLI and initialize your project:
```bash
eb init
```

2. Create and deploy your environment:
```bash
eb create neural-style-env
```

## Usage

1. Upload a content image (the photo you want to transform)
2. Upload a style image (the artistic style to apply)
3. Adjust parameters:
   - Optimization Steps: More steps give better results but take longer
   - Content Weight (α): Higher values preserve more of the original content
   - Style Weight (β): Higher values apply more of the artistic style
4. Click "Transfer Style" and wait for processing
5. View and download your result

## Technical Details

This application uses:
- PyTorch for the neural network backend
- VGG19 pretrained model for feature extraction
- Flask for the web server
- Bootstrap for the frontend UI

## License

MIT

## Credits

Based on the Neural Style Transfer algorithm by Gatys et al.