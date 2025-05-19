import torch
import torch.nn as nn
import torchvision.models as models
from torchvision.utils import save_image
from PIL import Image
import torchvision.transforms as transforms

class VGG(nn.Module):
    def __init__(self):
        super(VGG, self).__init__()
        self.chosen_features = ['0', '5', '10', '19', '28']
        # Use weights parameter instead of deprecated pretrained parameter
        self.model = models.vgg19(weights=models.VGG19_Weights.IMAGENET1K_V1).features[:29]
        
    def forward(self, x):
        features = []
        for layer_num, layer in enumerate(self.model):
            x = layer(x)
            if str(layer_num) in self.chosen_features:
                features.append(x)
        return features

class StyleTransfer:
    def __init__(self, image_size=356):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.image_size = image_size
        self.model = VGG().to(self.device).eval()
        self.loader = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor()
        ])
        
    def load_image(self, image_path):
        image = Image.open(image_path)
        image = self.loader(image).unsqueeze(0)
        return image.to(self.device)
    
    def transfer_style(self, content_img_path, style_img_path, output_path="generated.png", 
                      total_steps=3000, learning_rate=0.001, alpha=1, beta=0.01, progress_callback=None):
        """
        Transfer the style from style_img to content_img
        
        Parameters:
        - content_img_path: path to the content image
        - style_img_path: path to the style image
        - output_path: path to save the generated image
        - total_steps: number of optimization steps
        - learning_rate: learning rate for optimization
        - alpha: weight for content loss
        - beta: weight for style loss
        - progress_callback: function to call with progress updates (0-100)
        
        Returns:
        - Path to the generated image
        """
        # Load images
        content_img = self.load_image(content_img_path)
        style_img = self.load_image(style_img_path)
        
        # Start with the content image as initial guess
        generated = content_img.clone().requires_grad_(True)
        
        # Setup optimizer
        optimizer = torch.optim.Adam([generated], lr=learning_rate)
        
        # Initial progress update
        if progress_callback:
            progress_callback(0, "Starting style transfer")
            
        for step in range(total_steps):
            # Extract features
            generated_features = self.model(generated)
            content_features = self.model(content_img)
            style_features = self.model(style_img)
            
            # Calculate losses
            style_loss = content_loss = 0
            
            for gen_feature, content_feature, style_feature in zip(
                generated_features, content_features, style_features
            ):
                # Content loss
                batch_size, channel, height, width = gen_feature.shape
                content_loss += torch.mean((gen_feature - content_feature) ** 2)
                
                # Style loss - gram matrix
                G = gen_feature.view(channel, height * width).mm(
                    gen_feature.view(channel, height * width).t()
                )
                
                A = style_feature.view(channel, height * width).mm(
                    style_feature.view(channel, height * width).t()
                )
                
                style_loss += torch.mean((G - A) ** 2)
            
            # Total loss
            total_loss = alpha * content_loss + beta * style_loss
            
            # Optimization step
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
            
            # Calculate and report progress
            progress = int((step + 1) / total_steps * 100)
            if progress_callback:
                status = f"Step {step+1}/{total_steps}, Loss: {total_loss.item():.2f}"
                progress_callback(progress, status)
            
            # Save intermediate results
            if step % 500 == 0 or step == total_steps-1:
                print(f"Step {step+1}/{total_steps}, Loss: {total_loss.item():.2f}")
                intermediate_path = f"{output_path.split('.')[0]}_{step}.png"
                save_image(generated, intermediate_path)
                
        # Save final result
        save_image(generated, output_path)
        
        # Final progress update
        if progress_callback:
            progress_callback(100, "Style transfer complete!")
            
        return output_path