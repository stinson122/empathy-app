import json
import os
from pathlib import Path

def load_json_file(file_path):
    """Load JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def save_json_file(data, file_path):
    """Save data to a JSON file with pretty formatting."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved combined data to {file_path}")
    except Exception as e:
        print(f"Error saving {file_path}: {e}")

def get_product_type(product_name):
    """Determine product type based on product name."""
    product_name_lower = product_name.lower()
    if 'sunscreen' in product_name_lower:
        return 'Sunscreen'
    elif 'cleanser' in product_name_lower:
        return 'Cleanser'
    else:
        return 'Other'  # Fallback, though all products should be classified

def combine_data(posts_data, products_data):
    """
    Combine posts and products data by product name.
    
    Args:
        posts_data: List of products with their posts
        products_data: Dictionary of products with their megathread comments
        
    Returns:
        Dictionary with combined data by product
    """
    combined = {}
    
    # First, add all products from products_data
    for product_name, product_data in products_data.items():
        product_type = get_product_type(product_name)
        combined[product_name] = {
            'product_name': product_name,
            'product_type': product_type,
            'posts': [],
            'megathread_comments': [dict(comment, product_type=product_type) 
                                 for comment in product_data.get('megathread_comments', [])],
            'posts_count': 0,
            'comments_count': product_data.get('comments_count', 0)
        }
    
    # Then, add posts from posts_data
    for post_entry in posts_data:
        product_name = post_entry.get('product_name')
        if not product_name:
            continue
            
        # Add or update the product in combined data
        if product_name not in combined:
            product_type = get_product_type(product_name)
            combined[product_name] = {
                'product_name': product_name,
                'product_type': product_type,
                'posts': [],
                'megathread_comments': [],
                'posts_count': 0,
                'comments_count': 0
            }
            
        combined[product_name]['posts'].extend(post_entry.get('posts', []))
        combined[product_name]['posts_count'] = len(combined[product_name]['posts'])
    
    return combined

def main():
    # Define base directories
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / 'frontend' / 'public' / 'scrapes'
    output_dir = input_dir
    
    # Process both high and low confidence files
    for confidence in ['high', 'low']:
        print(f"\nProcessing {confidence} confidence data...")
        
        # Define file paths
        posts_file = input_dir / f'posts_grouped_{confidence}_confidence.json'
        products_file = input_dir / f'products_grouped_{confidence}_confidence.json'
        output_file = output_dir / f'combined_data_{confidence}_confidence.json'
        
        # Load data
        print(f"Loading {posts_file}...")
        posts_data = load_json_file(posts_file) or []
        
        print(f"Loading {products_file}...")
        products_data = load_json_file(products_file) or {}
        
        if not posts_data and not products_data:
            print(f"No data found for {confidence} confidence. Skipping...")
            continue
            
        # Combine data
        print("Combining data...")
        combined_data = combine_data(posts_data, products_data)
        
        # Save combined data
        print(f"Saving combined data to {output_file}...")
        save_json_file(combined_data, output_file)

if __name__ == "__main__":
    main()