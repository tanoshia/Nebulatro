#!/usr/bin/env python3
"""
Data Generator - Creates synthetic training data from game assets
"""

import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import random
from pathlib import Path
import json


class BalatroCardDataset(Dataset):
    """Dataset for Balatro cards with synthetic augmentations"""
    
    def __init__(self, cards_dir="resources/textures/2x", 
                 modifiers_dir="resources/textures/2x",
                 transform=None, augment_modifiers=True):
        """
        Args:
            cards_dir: Directory containing card textures
            modifiers_dir: Directory containing modifier textures
            transform: PyTorch transforms to apply
            augment_modifiers: Whether to generate modifier combinations
        """
        self.cards_dir = Path(cards_dir)
        self.modifiers_dir = Path(modifiers_dir)
        self.transform = transform or self.get_default_transforms()
        self.augment_modifiers = augment_modifiers
        
        # Load card templates
        self.cards = self._load_cards()
        self.modifiers = self._load_modifiers()
        
        # Generate synthetic dataset
        self.samples = self._generate_samples()
        
    def _load_cards(self):
        """Load all card templates"""
        cards = {}
        
        # Load playing cards from 8BitDeck.png
        deck_path = self.cards_dir / "8BitDeck.png"
        if deck_path.exists():
            deck_img = Image.open(deck_path).convert('RGBA')
            card_w = deck_img.width // 13
            card_h = deck_img.height // 4
            
            for row in range(4):  # 4 suits
                for col in range(13):  # 13 ranks
                    left = col * card_w
                    top = row * card_h
                    card = deck_img.crop((left, top, left + card_w, top + card_h))
                    
                    # Convert to RGB with white background
                    if card.mode == 'RGBA':
                        white_bg = Image.new('RGB', card.size, (255, 255, 255))
                        white_bg.paste(card, mask=card.split()[3])
                        card = white_bg
                    
                    card_idx = row * 13 + col
                    cards[card_idx] = card
        
        # TODO: Load jokers from Jokers.png (16x10 grid)
        # jokers_path = self.cards_dir / "Jokers.png"
        
        return cards
    
    def _load_modifiers(self):
        """Load modifier templates"""
        modifiers = {
            'enhancements': {},
            'editions': {},
            'seals': {}
        }
        
        # Load enhancements from Enhancers.png
        enhancers_path = self.modifiers_dir / "Enhancers.png"
        if enhancers_path.exists():
            # TODO: Extract enhancement sprites based on grid layout
            pass
        
        # Load editions (foil, holo, etc.)
        # TODO: Load from appropriate texture files
        
        return modifiers
    
    def _generate_samples(self):
        """Generate synthetic training samples"""
        samples = []
        
        # Generate base cards (no modifiers)
        for card_idx, card_img in self.cards.items():
            samples.append({
                'image': card_img,
                'card_class': card_idx,
                'modifiers': {'enhancement': 0, 'edition': 0, 'seal': 0}  # 0 = none
            })
        
        if self.augment_modifiers:
            # Generate cards with modifiers
            # TODO: Composite modifiers onto cards
            pass
        
        return samples
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Get full card image (no longer using corner region)
        image = sample['image']
        
        # Apply transforms
        if self.transform:
            image = self.transform(image)
        
        return {
            'image': image,
            'card_class': torch.tensor(sample['card_class'], dtype=torch.long),
            'modifiers': {
                k: torch.tensor(v, dtype=torch.long) 
                for k, v in sample['modifiers'].items()
            }
        }
    
    @staticmethod
    def get_default_transforms():
        """Default transforms for training"""
        return transforms.Compose([
            transforms.Resize((128, 128)),  # Resize to fixed size
            transforms.RandomRotation(5),   # Small rotations
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.RandomHorizontalFlip(p=0.1),  # Rare horizontal flip
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])  # ImageNet normalization
        ])
    
    @staticmethod
    def get_validation_transforms():
        """Transforms for validation (no augmentation)"""
        return transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])


class RealDatasetFromScreenshots(Dataset):
    """Dataset from manually labeled screenshots"""
    
    def __init__(self, data_dir="dataset/processed", transform=None):
        """
        Args:
            data_dir: Directory containing labeled card images
            transform: PyTorch transforms
        """
        self.data_dir = Path(data_dir)
        self.transform = transform or BalatroCardDataset.get_validation_transforms()
        
        # Load labeled data
        self.samples = self._load_labeled_data()
    
    def _load_labeled_data(self):
        """Load manually labeled card images"""
        samples = []
        
        # Expected structure:
        # dataset/processed/
        #   cards/
        #     0/  (2 of Hearts)
        #       image_001.png
        #       image_002.png
        #     1/  (3 of Hearts)
        #       ...
        
        cards_dir = self.data_dir / "cards"
        if cards_dir.exists():
            for class_dir in cards_dir.iterdir():
                if class_dir.is_dir() and class_dir.name.isdigit():
                    class_idx = int(class_dir.name)
                    
                    for img_file in class_dir.glob("*.png"):
                        samples.append({
                            'image_path': img_file,
                            'card_class': class_idx
                        })
        
        return samples
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load image
        image = Image.open(sample['image_path']).convert('RGB')
        
        # Apply transforms
        if self.transform:
            image = self.transform(image)
        
        return {
            'image': image,
            'card_class': torch.tensor(sample['card_class'], dtype=torch.long)
        }