# -*- coding: utf-8 -*-

import cv2
import numpy as np
from google.colab.patches import cv2_imshow

image_path = "/content/Inpaint_1.jpeg"
image = cv2.imread(image_path)

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

_, mask = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)

kernel = np.ones((5, 5), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

inpainted = cv2.inpaint(image, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

cv2_imshow(image)       # Original Image
cv2_imshow(mask)        # Refined Mask
cv2_imshow(inpainted)   # Inpainted Image

import cv2
import numpy as np
import matplotlib.pyplot as plt

def create_blending_mask(img1, img2, overlap_width):
    """Creates a gradient mask for blending."""
    mask1 = np.zeros((max(img1.shape[0], img2.shape[0]), img1.shape[1]), dtype=np.float32)
    mask2 = np.zeros((max(img1.shape[0], img2.shape[0]), img2.shape[1]), dtype=np.float32)

    mask1[:, :-overlap_width] = 1.0
    mask1[:, -overlap_width:] = np.linspace(1.0, 0.0, overlap_width)

    mask2[:, :overlap_width] = np.linspace(0.0, 1.0, overlap_width)
    mask2[:, overlap_width:] = 1.0

    return mask1, mask2

img1 = cv2.imread("Left.png")
img2 = cv2.imread("Right.png")

if img1 is None or img2 is None:
    raise FileNotFoundError("Could not load one or both of the images. Make sure 'Left.png' and 'Right.png' are in the correct directory.")

gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

sift = cv2.SIFT_create()
kp1, des1 = sift.detectAndCompute(gray1, None)
kp2, des2 = sift.detectAndCompute(gray2, None)

FLANN_INDEX_KDTREE = 1
index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
search_params = dict(checks=100)

flann = cv2.FlannBasedMatcher(index_params, search_params)
matches = flann.knnMatch(des1, des2, k=2)

good_matches = []
for m, n in matches:
    if m.distance < 0.6 * n.distance:
        good_matches.append(m)

if len(good_matches) < 10:
    raise Exception("Not enough good matches found. Panorama stitching might fail.")

src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0, confidence=0.99)

if H is None:
    raise Exception("Homography could not be computed. Check feature matching.")

height = max(img1.shape[0], img2.shape[0])
width = img1.shape[1] + img2.shape[1]
warped_img2 = cv2.warpPerspective(img2, H, (width, height))
stitched_img = np.zeros((height, width, 3), dtype=np.uint8)
stitched_img[:img1.shape[0], :img1.shape[1]] = img1

overlap_width = 50
blend_start = img1.shape[1] - overlap_width
blend_end = img1.shape[1]

blend_mask = np.linspace(1, 0, overlap_width).reshape(1, overlap_width, 1)

roi1 = stitched_img[:img1.shape[0], blend_start:blend_end].astype(np.float32)
roi2 = warped_img2[:img1.shape[0], blend_start:blend_end].astype(np.float32)

blended_roi = (roi1 * blend_mask + roi2 * (1 - blend_mask)).astype(np.uint8)

stitched_img[:img1.shape[0], blend_start:blend_end] = blended_roi

stitched_img[:img2.shape[0], img1.shape[1]:] = warped_img2[:img2.shape[0], img1.shape[1]:]

gray_stitched = cv2.cvtColor(stitched_img, cv2.COLOR_BGR2GRAY)
_, thresh_stitched = cv2.threshold(gray_stitched, 1, 255, cv2.THRESH_BINARY)
contours_stitched, _ = cv2.findContours(thresh_stitched, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if contours_stitched:
    x, y, w, h = cv2.boundingRect(contours_stitched[0])
    final_result = stitched_img[y:y+h, x:x+w]
else:
    final_result = stitched_img

plt.figure(figsize=(12, 6))
plt.imshow(cv2.cvtColor(final_result, cv2.COLOR_BGR2RGB))
plt.title("Improved Panorama Stitching with Direct Gradient Blend")
plt.axis('off')
plt.show()

"""<h4>Task 2</h4>"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
import numpy as np
import seaborn as sns
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt

device= torch.device("cuda" if torch.cuda.is_available() else "cpu")

transforms = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize([0.5,0.5,0.5], [0.5,0.5,0.5]),
    transforms.Lambda(lambda x: x.to(device))

])

train_dataset = datasets.CIFAR10(root='CIFAR/', train=True, transform=transforms, download=True)
test_dataset = datasets.CIFAR10(root='CIFAR/', train=False, transform=transforms, download=True)

train_loader = torch.utils.data.DataLoader(dataset=train_dataset, batch_size=64, shuffle=True)
test_loader = torch.utils.data.DataLoader(dataset=test_dataset, batch_size=64, shuffle=False)

class ConvAutoEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 32, 3, stride=3, padding=1), nn.ReLU(True),
            # for input shape (2,1,28,28)
            # output is (2,32,10,10)
            nn.MaxPool2d(2, stride=2),
            # output is (2,32,5,5)
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(True),
            #outpur is (2,64,3,3)
            nn.MaxPool2d(2, stride=1)
            #output is (2,64,2,2)
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(64, 32, 3, stride=2), nn.ReLU(True),
            #output is (2,32,5,5)
            nn.ConvTranspose2d(32, 16, 5, stride=3, padding=1), nn.ReLU(True),
            # output is (2,16,15,15)
            nn.ConvTranspose2d(16, 1, 2, stride=2, padding=1), nn.Tanh()
            # output is (2,1,28,28)
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        print(x.shape)
        return x

class AEModel(nn.Module):
    def __init__(self, cin, cout, stride=1, groups=1):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(cin, 64, 3, stride=3, padding=1), nn.ReLU(True),
            nn.MaxPool2d(2, stride=2),
            nn.Conv2d(64, cout, 3, stride=2, padding=1), nn.ReLU(True),
            nn.MaxPool2d(2, stride=1)
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(cout, 64, 3, stride=2), nn.ReLU(True),
            nn.ConvTranspose2d(64, 32, 5, stride=3, padding=1), nn.ReLU(True),
            nn.ConvTranspose2d(32, cin, 4, stride=2), nn.Tanh()
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x

model_test = AEModel(3,128)
model_test(torch.rand(2,3,32,32)).shape

def train (model,train_loader,loss,opt,device):
    model.train()
    loss_history=[]
    for true_image,_ in train_loader:
        opt.zero_grad()
        true_image=true_image.to(device)
        generated_image=model(true_image)
        lss=loss(generated_image,true_image)
        lss.backward()
        opt.step()
        loss_history.append(lss.item())
    return np.mean(loss_history)

def val (model,test_loader,loss,device):
    model.eval()
    loss_history=[]
    with torch.no_grad():
        for val_image,_ in test_loader:
            true_image=val_image.to(device)
            generated_image=model(true_image)
            lss=loss(generated_image,true_image)
            loss_history.append(lss.item())
    return np.mean(loss_history)

model = AEModel(3,128).to(device)
criterion = nn.MSELoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-5)

num_epochs = 20
trainl=[]
testl=[]
for epoch in range(num_epochs):
    train_loss = train(model,train_loader, criterion, optimizer,device)
    loss = val( model,test_loader, criterion,device)
    trainl.append(train_loss)
    testl.append(loss)
    print(f'epoic {epoch+1}   ||  training loss is {train_loss} ||   val loss is {loss}')

plt.figure()
epochs=[epoch for epoch in range (num_epochs)]
plt.plot(epochs, trainl, 'b', color='red',label='Training loss')
plt.plot(epochs, testl, 'b', label='Validation loss')
plt.title('Training and validation loss')
plt.legend()
plt.show()

def show(img, ax=None, title=None):
    """Utility function to display an image"""
    if ax is None:
        ax = plt.gca()
    img = img.cpu().detach().numpy()
    if img.shape[0] == 1:  # Grayscale image
        img = img[0]
        ax.imshow(img, cmap='gray')
    else:  # RGB image
        img = img.transpose((1, 2, 0))  # Convert to HWC format
        ax.imshow(img)
    if title is not None:
        ax.set_title(title)
    ax.axis('off')

for _ in range(10):
    ix = np.random.randint(len(test_dataset))
    im, _ = test_dataset[ix]
    _im = model(im.unsqueeze(0).to(device))[0]
    fig, ax = plt.subplots(1, 2, figsize=(6, 3))
    show(im, ax=ax[0], title='Input')
    show(_im, ax=ax[1], title='Prediction')
    plt.tight_layout()
    plt.show()

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
import numpy as np
import matplotlib.pyplot as plt

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,)),
    transforms.Lambda(lambda x: x.to(device))
])

train_dataset = datasets.MNIST(root='MNIST/', train=True, transform=transform, download=True)
test_dataset = datasets.MNIST(root='MNIST/', train=False, transform=transform, download=True)

train_loader = torch.utils.data.DataLoader(dataset=train_dataset, batch_size=64, shuffle=True)
test_loader = torch.utils.data.DataLoader(dataset=test_dataset, batch_size=64, shuffle=False)

class ConvAutoEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 32, 3, stride=1, padding=1), nn.ReLU(True),  # Keep output 28x28
            nn.MaxPool2d(2, stride=2),  # Output size: (batch, 32, 14, 14)
            nn.Conv2d(32, 64, 3, stride=1, padding=1), nn.ReLU(True),  # Output size: (batch, 64, 14, 14)
            nn.MaxPool2d(2, stride=2)  # Output size: (batch, 64, 7, 7)
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1), nn.ReLU(True),  # Output size: (batch, 32, 14, 14)
            nn.ConvTranspose2d(32, 16, 3, stride=2, padding=1, output_padding=1), nn.ReLU(True),  # Output size: (batch, 16, 28, 28)
            nn.ConvTranspose2d(16, 1, 3, stride=1, padding=1), nn.Tanh()  # Output size: (batch, 1, 28, 28)
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x

model = ConvAutoEncoder().to(device)  # Use ConvAutoEncoder for MNIST (grayscale)
criterion = nn.MSELoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-5)

def train(model, train_loader, loss, opt, device):
    model.train()
    loss_history = []
    for true_image, _ in train_loader:
        opt.zero_grad()
        true_image = true_image.to(device)
        generated_image = model(true_image)
        lss = loss(generated_image, true_image)
        lss.backward()
        opt.step()
        loss_history.append(lss.item())
    return np.mean(loss_history)

def val(model, test_loader, loss, device):
    model.eval()
    loss_history = []
    with torch.no_grad():
        for val_image, _ in test_loader:
            true_image = val_image.to(device)
            generated_image = model(true_image)
            lss = loss(generated_image, true_image)
            loss_history.append(lss.item())
    return np.mean(loss_history)

num_epochs = 20
trainl = []
testl = []

for epoch in range(num_epochs):
    train_loss = train(model, train_loader, criterion, optimizer, device)
    loss = val(model, test_loader, criterion, device)
    trainl.append(train_loss)
    testl.append(loss)
    print(f'Epoch {epoch+1}   ||  Training loss: {train_loss} ||   Validation loss: {loss}')

plt.figure()
epochs = [epoch for epoch in range(num_epochs)]
plt.plot(epochs, trainl, 'b', color='red', label='Training loss')
plt.plot(epochs, testl, 'b', label='Validation loss')
plt.title('Training and Validation Loss')
plt.legend()
plt.show()

def show(img, ax=None, title=None):
    """Utility function to display an image"""
    if ax is None:
        ax = plt.gca()
    img = img.cpu().detach().numpy()
    if img.shape[0] == 1:  # Grayscale image
        img = img[0]
        ax.imshow(img, cmap='gray')
    else:  # RGB image
        img = img.transpose((1, 2, 0))  # Convert to HWC format
        ax.imshow(img)
    if title is not None:
        ax.set_title(title)
    ax.axis('off')

for _ in range(10):
    ix = np.random.randint(len(test_dataset))
    im, _ = test_dataset[ix]
    _im = model(im.unsqueeze(0).to(device))[0]
    fig, ax = plt.subplots(1, 2, figsize=(6, 3))
    show(im, ax=ax[0], title='Input')
    show(_im, ax=ax[1], title='Prediction')
    plt.tight_layout()
    plt.show()

from __future__ import print_function
import os
import random
import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
import torch.optim as optim
import torch.utils.data
import torchvision.datasets as dset
import torchvision.transforms as transforms
import torchvision.utils as vutils
import matplotlib.pyplot as plt

cudnn.benchmark = True

manualSeed = random.randint(1, 10000)
print("Random Seed: ", manualSeed)
random.seed(manualSeed)
torch.manual_seed(manualSeed)

os.makedirs("output", exist_ok=True)
os.makedirs("weights", exist_ok=True)

dataset = dset.CIFAR10(
    root="./data", download=True,
    transform=transforms.Compose([
        transforms.Resize(64),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
    ])
)

nc = 3
dataloader = torch.utils.data.DataLoader(dataset, batch_size=128, shuffle=True, num_workers=2)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print("Using device:", device)

ngpu = 1
nz = 100
ngf = 64
ndf = 64

def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        m.weight.data.normal_(0.0, 0.02)
    elif classname.find('BatchNorm') != -1:
        m.weight.data.normal_(1.0, 0.02)
        m.bias.data.fill_(0)

class Generator(nn.Module):
    def __init__(self, ngpu):
        super(Generator, self).__init__()
        self.ngpu = ngpu
        self.main = nn.Sequential(
            nn.ConvTranspose2d(nz, ngf * 8, 4, 1, 0, bias=False),
            nn.BatchNorm2d(ngf * 8),
            nn.ReLU(True),
            nn.ConvTranspose2d(ngf * 8, ngf * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 4),
            nn.ReLU(True),
            nn.ConvTranspose2d(ngf * 4, ngf * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf * 2),
            nn.ReLU(True),
            nn.ConvTranspose2d(ngf * 2, ngf, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ngf),
            nn.ReLU(True),
            nn.ConvTranspose2d(ngf, nc, 4, 2, 1, bias=False),
            nn.Tanh()
        )

    def forward(self, input):
        return self.main(input)

netG = Generator(ngpu).to(device)
netG.apply(weights_init)
print(netG)

class Discriminator(nn.Module):
    def __init__(self, ngpu):
        super(Discriminator, self).__init__()
        self.ngpu = ngpu
        self.main = nn.Sequential(
            nn.Conv2d(nc, ndf, 4, 2, 1, bias=False),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(ndf, ndf * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 2),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(ndf * 2, ndf * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 4),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(ndf * 4, ndf * 8, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 8),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(ndf * 8, 1, 4, 1, 0, bias=False),
            nn.Sigmoid()
        )

    def forward(self, input):
        return self.main(input).view(-1, 1).squeeze(1)

netD = Discriminator(ngpu).to(device)
netD.apply(weights_init)
print(netD)

criterion = nn.BCELoss()
optimizerD = optim.Adam(netD.parameters(), lr=0.0002, betas=(0.5, 0.999))
optimizerG = optim.Adam(netG.parameters(), lr=0.0002, betas=(0.5, 0.999))

fixed_noise = torch.randn(128, nz, 1, 1, device=device)
real_label = 1
fake_label = 0
niter = 25

for epoch in range(niter):
    for i, data in enumerate(dataloader, 0):
        netD.zero_grad()
        real_cpu = data[0].to(device)
        batch_size = real_cpu.size(0)

        label = torch.full((batch_size,), real_label, device=device, dtype=torch.float)

        output = netD(real_cpu)
        errD_real = criterion(output, label)
        errD_real.backward()
        D_x = output.mean().item()

        noise = torch.randn(batch_size, nz, 1, 1, device=device)
        fake = netG(noise)
        label.fill_(fake_label)
        output = netD(fake.detach())
        errD_fake = criterion(output, label)
        errD_fake.backward()
        D_G_z1 = output.mean().item()
        errD = errD_real + errD_fake
        optimizerD.step()

        netG.zero_grad()
        label.fill_(real_label)
        output = netD(fake)
        errG = criterion(output, label)
        errG.backward()
        D_G_z2 = output.mean().item()
        optimizerG.step()


        if i % 50 == 0:
            print('[%d/%d][%d/%d] Loss_D: %.4f Loss_G: %.4f D(x): %.4f D(G(z)): %.4f / %.4f' %
                  (epoch, niter, i, len(dataloader), errD.item(), errG.item(), D_x, D_G_z1, D_G_z2))

        if i % 100 == 0:
            vutils.save_image(real_cpu, 'output/real_samples.png', normalize=True)
            fake = netG(fixed_noise)
            vutils.save_image(fake.detach(), f'output/fake_samples_epoch_{epoch:03d}.png', normalize=True)

    torch.save(netG.state_dict(), f'weights/netG_epoch_{epoch}.pth')
    torch.save(netD.state_dict(), f'weights/netD_epoch_{epoch}.pth')

import os
from IPython.display import Image, display

output_path = "/content/output"

image_files = sorted([f for f in os.listdir(output_path) if f.endswith(('.png', '.jpg', '.jpeg'))])

for img_file in image_files:
    display(Image(filename=os.path.join(output_path, img_file)))

import tensorflow as tf
from tensorflow.keras import layers
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

(train_images, train_labels), (_, _) = tf.keras.datasets.mnist.load_data()
train_images = (train_images.astype("float32") - 127.5) / 127.5
train_images = np.expand_dims(train_images, axis=-1)
BUFFER_SIZE = 60000
BATCH_SIZE = 256
dataset = tf.data.Dataset.from_tensor_slices(train_images).shuffle(BUFFER_SIZE).batch(BATCH_SIZE)

def build_generator():
    model = tf.keras.Sequential([
        layers.Dense(7*7*256, use_bias=False, input_shape=(100,)),
        layers.BatchNormalization(),
        layers.LeakyReLU(),
        layers.Reshape((7, 7, 256)),
        layers.Conv2DTranspose(128, (5, 5), strides=(1, 1), padding='same', use_bias=False),
        layers.BatchNormalization(),
        layers.LeakyReLU(),
        layers.Conv2DTranspose(64, (5, 5), strides=(2, 2), padding='same', use_bias=False),
        layers.BatchNormalization(),
        layers.LeakyReLU(),
        layers.Conv2DTranspose(1, (5, 5), strides=(2, 2), padding='same', use_bias=False, activation='tanh')
    ])
    return model

def build_discriminator():
    model = tf.keras.Sequential([
        layers.Conv2D(64, (5, 5), strides=(2, 2), padding='same', input_shape=[28, 28, 1]),
        layers.LeakyReLU(),
        layers.Dropout(0.3),
        layers.Conv2D(128, (5, 5), strides=(2, 2), padding='same'),
        layers.LeakyReLU(),
        layers.Dropout(0.3),
        layers.Flatten(),
        layers.Dense(1, activation='sigmoid')
    ])
    return model

def generator_loss(fake_output):
    return tf.keras.losses.BinaryCrossentropy(from_logits=True)(tf.ones_like(fake_output), fake_output)

def discriminator_loss(real_output, fake_output):
    real_loss = tf.keras.losses.BinaryCrossentropy(from_logits=True)(tf.ones_like(real_output), real_output)
    fake_loss = tf.keras.losses.BinaryCrossentropy(from_logits=True)(tf.zeros_like(fake_output), fake_output)
    return real_loss + fake_loss

generator = build_generator()
discriminator = build_discriminator()

generator_optimizer = tf.keras.optimizers.Adam(1e-4)
discriminator_optimizer = tf.keras.optimizers.Adam(1e-4)

@tf.function
def train_step(images):
    noise = tf.random.normal([BATCH_SIZE, 100])
    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
        generated_images = generator(noise, training=True)
        real_output = discriminator(images, training=True)
        fake_output = discriminator(generated_images, training=True)
        gen_loss = generator_loss(fake_output)
        disc_loss = discriminator_loss(real_output, fake_output)
    gradients_of_generator = gen_tape.gradient(gen_loss, generator.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminator.trainable_variables)
    generator_optimizer.apply_gradients(zip(gradients_of_generator, generator.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminator.trainable_variables))

def generate_and_show_images(epoch, noise_dim=100):
    noise = tf.random.normal([16, noise_dim])
    generated_images = generator(noise, training=False)
    fig = plt.figure(figsize=(4, 4))
    for i in range(generated_images.shape[0]):
        plt.subplot(4, 4, i + 1)
        plt.imshow(generated_images[i, :, :, 0] * 127.5 + 127.5, cmap='gray')
        plt.axis('off')
    plt.suptitle(f"Epoch {epoch}")
    plt.show()

def train(dataset, epochs, display_interval=10):
    for epoch in range(epochs):
        for image_batch in dataset:
            train_step(image_batch)
        print(f"Epoch {epoch+1} completed")
        if (epoch) % display_interval == 0:
            generate_and_show_images(epoch + 1)

EPOCHS = 100
train(dataset, EPOCHS, display_interval=1)

generate_and_show_images('final')

!kaggle competitions download -c dog-breed-identification
!unzip dog-breed-identification.zip -d dog_breeds

!mkdir -p ~/.kaggle
!cp kaggle.json ~/.kaggle/
!chmod 600 ~/.kaggle/kaggle.json

!kaggle competitions download -c dog-breed-identification
!unzip dog-breed-identification.zip -d dog_breeds

"""<h4>V2</h4>"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model

labels_df = pd.read_csv('dog_breeds/labels.csv')

image_dir = 'dog_breeds/train/'
image_size = 224
batch_size = 32

labels_df['id'] = labels_df['id'].apply(lambda x: x + '.jpg')

train_df, val_df = train_test_split(labels_df, test_size=0.2, stratify=labels_df['breed'])

datagen = ImageDataGenerator(preprocessing_function=preprocess_input)

train_gen = datagen.flow_from_dataframe(
    dataframe=train_df,
    directory=image_dir,
    x_col='id',
    y_col='breed',
    target_size=(image_size, image_size),
    class_mode='categorical',
    batch_size=batch_size
)

val_gen = datagen.flow_from_dataframe(
    dataframe=val_df,
    directory=image_dir,
    x_col='id',
    y_col='breed',
    target_size=(image_size, image_size),
    class_mode='categorical',
    batch_size=batch_size
)

from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model

base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(image_size, image_size, 3))

base_model.trainable = False

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)

num_classes = len(train_gen.class_indices)
predictions = Dense(num_classes, activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=5
)

import numpy as np

if not hasattr(np, 'Inf'):
    np.Inf = np.inf

plt.plot(history.history['accuracy'], label='Train Acc')
plt.plot(history.history['val_accuracy'], label='Val Acc')
plt.title('Accuracy')
plt.legend()
plt.show()

import matplotlib.pyplot as plt
import cv2
import random

sample_images = train_df.sample(9)

plt.figure(figsize=(12, 12))

for i, row in enumerate(sample_images.itertuples(), 1):
    img_path = os.path.join(image_dir, row.id)
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    plt.subplot(3, 3, i)
    plt.imshow(img)
    plt.title(row.breed)
    plt.axis('off')

plt.tight_layout()
plt.show()
test_dir = 'dog_breeds/test/'

test_files = os.listdir(test_dir)
test_df = pd.DataFrame({'id': test_files})
test_df['id'] = test_df['id'].apply(lambda x: x)

test_gen = datagen.flow_from_dataframe(
    dataframe=test_df,
    directory=test_dir,
    x_col='id',
    y_col=None,
    class_mode=None,
    target_size=(image_size, image_size),
    batch_size=1,
    shuffle=False
)

preds = model.predict(test_gen)
pred_labels = np.argmax(preds, axis=1)

"""<h4>V1</h4>"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNet
from tensorflow.keras.applications.mobilenet import preprocess_input
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model
import cv2

labels_df = pd.read_csv('dog_breeds/labels.csv')

image_dir = 'dog_breeds/train/'
image_size = 224
batch_size = 32

labels_df['id'] = labels_df['id'].apply(lambda x: x + '.jpg')

train_df, val_df = train_test_split(labels_df, test_size=0.2, stratify=labels_df['breed'])

datagen = ImageDataGenerator(preprocessing_function=preprocess_input)

train_gen = datagen.flow_from_dataframe(
    dataframe=train_df,
    directory=image_dir,
    x_col='id',
    y_col='breed',
    target_size=(image_size, image_size),
    class_mode='categorical',
    batch_size=batch_size
)

val_gen = datagen.flow_from_dataframe(
    dataframe=val_df,
    directory=image_dir,
    x_col='id',
    y_col='breed',
    target_size=(image_size, image_size),
    class_mode='categorical',
    batch_size=batch_size
)

base_model = MobileNet(weights='imagenet', include_top=False, input_shape=(image_size, image_size, 3))

base_model.trainable = False

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)

num_classes = len(train_gen.class_indices)
predictions = Dense(num_classes, activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=5
)

plt.plot(history.history['accuracy'], label='Train Acc')
plt.plot(history.history['val_accuracy'], label='Val Acc')
plt.title('Accuracy')
plt.legend()
plt.show()

sample_images = train_df.sample(9)

plt.figure(figsize=(12, 12))

for i, row in enumerate(sample_images.itertuples(), 1):
    img_path = os.path.join(image_dir, row.id)
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    plt.subplot(3, 3, i)
    plt.imshow(img)
    plt.title(row.breed)
    plt.axis('off')

plt.tight_layout()
plt.show()

test_dir = 'dog_breeds/test/'
test_files = os.listdir(test_dir)
test_df = pd.DataFrame({'id': test_files})
test_df['id'] = test_df['id'].apply(lambda x: x)

test_gen = datagen.flow_from_dataframe(
    dataframe=test_df,
    directory=test_dir,
    x_col='id',
    y_col=None,
    class_mode=None,
    target_size=(image_size, image_size),
    batch_size=1,
    shuffle=False
)

preds = model.predict(test_gen)

pred_labels = np.argmax(preds, axis=1)

"""<h4>V3</h4>"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV3Large  # MobileNetV3 Large variant
from tensorflow.keras.applications.mobilenet_v3 import preprocess_input
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model
import cv2

labels_df = pd.read_csv('dog_breeds/labels.csv')

image_dir = 'dog_breeds/train/'
image_size = 224
batch_size = 32

labels_df['id'] = labels_df['id'].apply(lambda x: x + '.jpg')

train_df, val_df = train_test_split(labels_df, test_size=0.2, stratify=labels_df['breed'])

datagen = ImageDataGenerator(preprocessing_function=preprocess_input)

train_gen = datagen.flow_from_dataframe(
    dataframe=train_df,
    directory=image_dir,
    x_col='id',
    y_col='breed',
    target_size=(image_size, image_size),
    class_mode='categorical',
    batch_size=batch_size
)

val_gen = datagen.flow_from_dataframe(
    dataframe=val_df,
    directory=image_dir,
    x_col='id',
    y_col='breed',
    target_size=(image_size, image_size),
    class_mode='categorical',
    batch_size=batch_size
)

base_model = MobileNetV3Large(weights='imagenet', include_top=False, input_shape=(image_size, image_size, 3))

base_model.trainable = False

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)

num_classes = len(train_gen.class_indices)
predictions = Dense(num_classes, activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=5
)

plt.plot(history.history['accuracy'], label='Train Acc')
plt.plot(history.history['val_accuracy'], label='Val Acc')
plt.title('Accuracy')
plt.legend()
plt.show()

sample_images = train_df.sample(9)

plt.figure(figsize=(12, 12))

for i, row in enumerate(sample_images.itertuples(), 1):
    img_path = os.path.join(image_dir, row.id)
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    plt.subplot(3, 3, i)
    plt.imshow(img)
    plt.title(row.breed)
    plt.axis('off')

plt.tight_layout()
plt.show()

test_dir = 'dog_breeds/test/'
test_files = os.listdir(test_dir)
test_df = pd.DataFrame({'id': test_files})
test_df['id'] = test_df['id'].apply(lambda x: x)

test_gen = datagen.flow_from_dataframe(
    dataframe=test_df,
    directory=test_dir,
    x_col='id',
    y_col=None,
    class_mode=None,
    target_size=(image_size, image_size),
    batch_size=1,
    shuffle=False
)

preds = model.predict(test_gen)

pred_labels = np.argmax(preds, axis=1)

import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dropout, UpSampling2D, Input, concatenate
from tensorflow.keras.models import Model
from sklearn.model_selection import train_test_split
import os
from PIL import Image

import tensorflow_datasets as tfds

dataset, info = tfds.load('oxford_iiit_pet', with_info=True)

def normalize(input_image, input_mask):
    input_image = tf.cast(input_image, tf.float32) / 255.0
    input_mask = tf.cast(input_mask, tf.uint8)
    input_mask -= 1
    input_mask = tf.where(input_mask == 1, 1, 0)
    return input_image, input_mask

def load_image(datapoint):
    input_image = tf.image.resize(datapoint['image'], (128, 128))
    input_mask = tf.image.resize(datapoint['segmentation_mask'], (128, 128))
    input_image, input_mask = normalize(input_image, input_mask)
    return input_image, input_mask

train = dataset['train'].map(load_image)
test = dataset['test'].map(load_image)

train_dataset = train.batch(32).prefetch(tf.data.AUTOTUNE)
test_dataset = test.batch(32).prefetch(tf.data.AUTOTUNE)

def unet_model(input_size=(128, 128, 3)):
    inputs = Input(input_size)

    # Encoder
    c1 = Conv2D(64, 3, activation='relu', padding='same')(inputs)
    c1 = Conv2D(64, 3, activation='relu', padding='same')(c1)
    p1 = MaxPooling2D()(c1)

    c2 = Conv2D(128, 3, activation='relu', padding='same')(p1)
    c2 = Conv2D(128, 3, activation='relu', padding='same')(c2)
    p2 = MaxPooling2D()(c2)

    # Bottleneck
    c3 = Conv2D(256, 3, activation='relu', padding='same')(p2)
    c3 = Conv2D(256, 3, activation='relu', padding='same')(c3)

    # Decoder
    u1 = UpSampling2D()(c3)
    u1 = concatenate([u1, c2])
    c4 = Conv2D(128, 3, activation='relu', padding='same')(u1)
    c4 = Conv2D(128, 3, activation='relu', padding='same')(c4)

    u2 = UpSampling2D()(c4)
    u2 = concatenate([u2, c1])
    c5 = Conv2D(64, 3, activation='relu', padding='same')(u2)
    c5 = Conv2D(64, 3, activation='relu', padding='same')(c5)

    outputs = Conv2D(1, 1, activation='sigmoid')(c5)

    model = Model(inputs, outputs)
    return model

model = unet_model()
model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

model.fit(train_dataset, validation_data=test_dataset, epochs=10)

def iou_metric(y_true, y_pred):
    y_true = tf.cast(y_true, tf.float32)
    y_pred = tf.cast(y_pred > 0.5, tf.float32)
    intersection = tf.reduce_sum(y_true * y_pred)
    union = tf.reduce_sum(y_true) + tf.reduce_sum(y_pred) - intersection
    return intersection / (union + 1e-7)

def dice_coefficient(y_true, y_pred):
    y_true = tf.cast(y_true, tf.float32)
    y_pred = tf.cast(y_pred > 0.5, tf.float32)
    intersection = tf.reduce_sum(y_true * y_pred)
    return (2. * intersection) / (tf.reduce_sum(y_true) + tf.reduce_sum(y_pred) + 1e-7)

for images, masks in test_dataset.take(1):
    preds = model.predict(images)
    iou = iou_metric(masks, preds).numpy()
    dice = dice_coefficient(masks, preds).numpy()

print(f"IoU Score: {iou:.4f}")
print(f"Dice Coefficient: {dice:.4f}")

import numpy as np
np.Inf = np.inf

import numpy as np

def display_sample(image, mask, pred_mask):

    if np.any(np.isinf(image)) or np.any(np.isinf(mask)) or np.any(np.isinf(pred_mask)):
        print("Detected np.Inf, replacing with np.inf")

    plt.figure(figsize=(10, 3))
    titles = ["Input Image", "True Mask", "Predicted Mask"]
    images = [image, mask, pred_mask]

    for i in range(3):
        plt.subplot(1, 3, i + 1)
        plt.title(titles[i])
        plt.imshow(tf.keras.utils.array_to_img(images[i]))
        plt.axis('off')
    plt.show()


for image, mask in test_dataset.take(1):
    pred_mask = model.predict(image)
    display_sample(image[0], mask[0], pred_mask[0])

