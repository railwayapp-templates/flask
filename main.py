from flask import Flask, render_template, request, jsonify
import torch
from torchvision import transforms
from PIL import Image
import io
import torch.nn as nn
import torch.nn.functional as F
import base64
from PIL import ImageOps

app = Flask(__name__)

class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(128 * 3 * 3, 128)
        self.fc2 = nn.Linear(128, 256)
        self.fc3 = nn.Linear(256, 512)
        self.fc4 = nn.Linear(512, 10)



    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.pool(F.relu(self.conv3(x)))
        x = x.view(-1, 128 * 3 * 3)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return x
    
model = CNN()
model = torch.load("model.pth",map_location=torch.device('cpu'))
# Define preprocessing transforms
transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=1),
    transforms.Resize((28, 28)),
    transforms.ToTensor(),
])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    # Get the image data from the POST request
    data = request.get_json()
    image_data = data["image"]

    # Decode base64 image data
    img = Image.open(io.BytesIO(base64.b64decode(image_data)))

    # Preprocess the image
    # img = img.convert("L")
    # img = ImageOps.invert(img)
    img = transform(img)
    img = img.unsqueeze(0)

    # Make prediction
    with torch.no_grad():
        output = model(img)
        probabilities = torch.softmax(output, dim=1)  # Convert logits to probabilities
        _, predicted = torch.max(output, 1)
        prediction = predicted.item()

    return jsonify({'prediction': prediction})

if __name__ == '__main__':
    app.run(debug=True)
