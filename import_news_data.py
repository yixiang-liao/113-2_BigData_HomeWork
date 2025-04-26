#!/usr/bin/env python
import os
import sys
import pandas as pd
import argparse
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django
django.setup()

# Now we can import Django models
from app_user_keyword_association.models import NewsData
from asgiref.sync import sync_to_async


def import_news_data(csv_file_path):
    """
    Import news data from CSV file to the database
    """
    print(f'Importing data from {csv_file_path}...')
    
    # Read CSV file
    df = pd.read_csv(csv_file_path, sep='|')
    
    # Count total records
    total_records = len(df)
    print(f'Found {total_records} records in CSV file')
    
    # Counter for imported records
    imported = 0
    
    # Process each row and create a NewsData object
    for _, row in df.iterrows():
        try:
            # Convert date string to datetime object
            date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()
            
            # Handle photo_link field 
            photo_link = None
            if 'photo_link' in row:
                if pd.isna(row['photo_link']):
                    # CSV中的欄位為空，被pandas讀取為NaN
                    photo_link = None
                elif row['photo_link'] == "":
                    # CSV中的欄位是空字串
                    photo_link = None
                else:
                    # CSV中的欄位有實際的URL值
                    photo_link = row['photo_link']
            
            # Create a dictionary with the data for the NewsData object
            data = {
                'date': date_obj,
                'category': row['category'],
                'title': row['title'],
                'content': row['content'],
                'sentiment': row['sentiment'] if 'sentiment' in row else None,
                'summary': row['summary'] if 'summary' in row else None,
                'top_key_freq': row['top_key_freq'] if 'top_key_freq' in row else None,
                'tokens': row['tokens'] if 'tokens' in row else None,
                'tokens_v2': row['tokens_v2'] if 'tokens_v2' in row else None,
                'entities': row['entities'] if 'entities' in row else None,
                'token_pos': row['token_pos'] if 'token_pos' in row else None,
                'link': row['link'] if 'link' in row else None,
                'photo_link': photo_link,
            }
            
            # Use update_or_create method to save the data (synchronously)
            try:
                news_data, created = NewsData.objects.update_or_create(
                    item_id=row['item_id'],
                    defaults=data
                )
                
                if created:
                    imported += 1
                    if imported % 100 == 0:
                        print(f'Imported {imported} records...')
                
            except django.db.utils.OperationalError as e:
                print(f"Database error: {e}")
                print("Trying alternative approach...")
                
                # Try creating a new object directly
                existing = NewsData.objects.filter(item_id=row['item_id']).exists()
                if not existing:
                    news_data = NewsData(item_id=row['item_id'], **data)
                    news_data.save()
                    imported += 1
                    if imported % 100 == 0:
                        print(f'Imported {imported} records...')
                else:
                    # Update existing object
                    NewsData.objects.filter(item_id=row['item_id']).update(**data)
                        
        except Exception as e:
            print(f'Error importing record {row["item_id"]}: {e}')
    
    print(f'Successfully imported {imported} news articles to the database')


# 提供一個異步的入口點，如果需要在異步環境中運行
async def async_import_news_data(csv_file_path):
    """
    Async wrapper for import_news_data
    """
    # 使用 sync_to_async 將同步函數轉換為異步函數
    import_func = sync_to_async(import_news_data)
    await import_func(csv_file_path)


if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Import news data from CSV file to database')
    parser.add_argument('--csv_file', type=str, 
                        default='app_user_keyword/dataset/cna_news_200_preprocessed.csv',
                        help='Path to CSV file with news data')
    parser.add_argument('--async_mode', action='store_true', 
                        help='Run in async mode if needed for async environments')
    
    args = parser.parse_args()
    
    # Run the import function
    if args.async_mode:
        import asyncio
        asyncio.run(async_import_news_data(args.csv_file))
    else:
        import_news_data(args.csv_file)