#!/usr/bin/env python3
"""
Setup ML Environment - Check dependencies and prepare for training
"""

import sys
import subprocess
from pathlib import Path


def check_pytorch():
    """Check PyTorch installation and CUDA availability"""
    try:
        import torch
        import torchvision
        
        print(f"✓ PyTorch {torch.__version__}")
        print(f"✓ TorchVision {torchvision.__version__}")
        
        if torch.cuda.is_available():
            print(f"✓ CUDA {torch.version.cuda}")
            print(f"✓ GPU: {torch.cuda.get_device_name(0)}")
            print(f"✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        elif torch.backends.mps.is_available():
            print("✓ MPS (Metal Performance Shaders) available")
            print("✓ GPU: Apple Silicon (M-series chip)")
        else:
            print("⚠ No GPU acceleration available - will use CPU")
        
        return True
    except ImportError as e:
        print(f"✗ PyTorch not installed: {e}")
        return False


def check_dependencies():
    """Check all required dependencies"""
    required = [
        'torch', 'torchvision', 'numpy', 'matplotlib', 
        'tqdm', 'sklearn', 'cv2', 'PIL'
    ]
    
    missing = []
    for package in required:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'PIL':
                from PIL import Image
            elif package == 'sklearn':
                import sklearn
            else:
                __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            missing.append(package)
    
    return len(missing) == 0, missing


def setup_directories():
    """Create necessary directories"""
    dirs = [
        "dataset/raw",
        "dataset/processed/cards",
        "models",
        "logs"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {dir_path}")


def check_game_assets():
    """Check if game assets are available"""
    assets = [
        "resources/textures/2x/8BitDeck.png",
        "resources/textures/2x/Enhancers.png",
        "resources/textures/2x/Jokers.png"
    ]
    
    available = []
    for asset in assets:
        if Path(asset).exists():
            print(f"✓ {asset}")
            available.append(asset)
        else:
            print(f"✗ {asset}")
    
    return available


def install_pytorch_cuda():
    """Install PyTorch with CUDA support"""
    print("Installing PyTorch with CUDA support...")
    
    # For CUDA 11.8 (adjust based on your CUDA version)
    cmd = [
        sys.executable, "-m", "pip", "install", 
        "torch", "torchvision", "torchaudio", 
        "--index-url", "https://download.pytorch.org/whl/cu118"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ PyTorch with CUDA installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install PyTorch: {e}")
        return False


def main():
    """Main setup function"""
    print("=== Balatro ML Training Setup ===\n")
    
    # Check dependencies
    print("Checking dependencies...")
    deps_ok, missing = check_dependencies()
    
    if not deps_ok:
        print(f"\nMissing dependencies: {missing}")
        print("Install with: pip install -r requirements.txt")
        
        # Offer to install PyTorch with CUDA
        if 'torch' in missing:
            response = input("\nInstall PyTorch with CUDA support? (y/n): ")
            if response.lower() == 'y':
                install_pytorch_cuda()
        
        return
    
    print("\n" + "="*50)
    
    # Check PyTorch specifically
    print("Checking PyTorch...")
    pytorch_ok = check_pytorch()
    
    print("\n" + "="*50)
    
    # Setup directories
    print("Setting up directories...")
    setup_directories()
    
    print("\n" + "="*50)
    
    # Check game assets
    print("Checking game assets...")
    available_assets = check_game_assets()
    
    print("\n" + "="*50)
    
    # Summary
    print("Setup Summary:")
    print(f"✓ Dependencies: {'OK' if deps_ok else 'Missing'}")
    print(f"✓ PyTorch: {'OK' if pytorch_ok else 'Missing'}")
    print(f"✓ Game Assets: {len(available_assets)}/3 available")
    
    if deps_ok and pytorch_ok and len(available_assets) > 0:
        print("\n🎉 Ready to start training!")
        print("\nNext steps:")
        print("1. Run: python train_card_classifier.py")
        print("2. Or collect real training data first")
    else:
        print("\n⚠ Setup incomplete. Please resolve issues above.")


if __name__ == "__main__":
    main()