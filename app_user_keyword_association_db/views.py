from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q, Max, F
from django.db.models.functions import Cast
from django.db.models import TextField

from datetime import datetime, timedelta
import pandas as pd
import math
import re
import json
from collections import Counter

# Import the NewsData model
from .models import NewsData

# For the key association analysis
def home(request):
    return render(request, 'app_user_keyword_association/home.html')


@csrf_exempt
def api_get_userkey_associate(request):
    userkey = request.POST.get('userkey')
    cate = request.POST['cate']  # This is an alternative way to get POST data.
    cond = request.POST.get('cond')
    weeks = int(request.POST.get('weeks'))
    key = userkey.split()

    # Get query results from database
    queryset = filter_database_fullText(key, cond, cate, weeks)
    print(f"Query returned {queryset.count()} results")

    if queryset.exists():  # queryset is not empty
        newslinks = get_title_link_topk(queryset, k=10)
        related_words, clouddata = get_related_word_clouddata(queryset)
        same_paragraph = get_same_para(queryset, key, cond, k=6)  # multiple keywords
        num_articles = queryset.count() # total number of articles (stories, items)
    else:
        newslinks = []
        related_words = []
        same_paragraph = []
        clouddata = []
        num_articles = 0

    response = {
        'num_articles': num_articles,
        'newslinks': newslinks,
        'related_words': related_words,
        'same_paragraph': same_paragraph,
        'clouddata': clouddata,
    }
    return JsonResponse(response)


# Searching keywords from "content" column
# This function now uses database queries instead of pandas
def filter_database_fullText(user_keywords, cond, cate, weeks):
    # Get the latest date in the database
    latest_date = NewsData.objects.aggregate(max_date=Max('date'))['max_date']
    
    # Calculate start date
    start_date = latest_date - timedelta(weeks=weeks)
    
    # Base query - filter by date range
    queryset = NewsData.objects.filter(date__gte=start_date, date__lte=latest_date)
    
    # Filter by category if not "全部"
    if cate != "全部":
        queryset = queryset.filter(category=cate)
    
    # Filter by keywords based on condition (AND or OR)
    if cond == 'and':
        # For AND condition, we need all keywords to be present
        for kw in user_keywords:
            queryset = queryset.filter(content__contains=kw)
    elif cond == 'or':
        # For OR condition, any keyword can be present
        q_objects = Q()
        for kw in user_keywords:
            q_objects |= Q(content__contains=kw)
        queryset = queryset.filter(q_objects)
    
    return queryset


# Get titles and links from k pieces of news
def get_title_link_topk(queryset, k=25):
    items = []
    # Limit to k results and get specific fields
    news_items = queryset.values('category', 'title', 'link', 'photo_link')[:k]
    
    for item in news_items:
        category = item['category']
        title = item['title']
        link = item['link'] or ''
        photo_link = item['photo_link'] or ''
        
        item_info = {
            'category': category,
            'title': title,
            'link': link,
            'photo_link': photo_link
        }
        
        items.append(item_info)
    return items


# Get related keywords by counting the top keywords of each news item
def get_related_word_clouddata(queryset):
    # Prepare counter for keywords
    counter = Counter()
    
    # Process each news item
    for news in queryset:
        if news.top_key_freq:
            try:
                # Convert the stored string representation to a dictionary
                pair_dict = dict(eval(news.top_key_freq))
                counter += Counter(pair_dict)
            except (SyntaxError, ValueError):
                # Skip if there's an error in the string format
                continue
    
    # Get the most common words
    wf_pairs = counter.most_common(20)
    
    # If no words found, return empty results
    if not wf_pairs:
        return [], []
    
    # Calculate cloud data
    min_ = wf_pairs[-1][1] if len(wf_pairs) > 0 else 0
    max_ = wf_pairs[0][1] if len(wf_pairs) > 0 else 0
    
    # Avoid division by zero
    if max_ == min_:
        clouddata = [{'text': w, 'size': 60} for w, f in wf_pairs]
    else:
        # Text size based on word frequency for drawing cloud chart
        textSizeMin = 20
        textSizeMax = 120
        # Scale the frequency value to a range from 20 to 120
        clouddata = [{'text': w, 'size': int(textSizeMin + (f - min_) / (max_ - min_) * (textSizeMax - textSizeMin))}
                    for w, f in wf_pairs]
    
    return wf_pairs, clouddata


# Split paragraphs in text
def cut_paragraph(text):
    if not text:
        return []
    
    paragraphs = text.split('。')  # 遇到句號就切開
    paragraphs = list(filter(None, paragraphs))
    return paragraphs


# Select all paragraphs where multiple keywords occur
def get_same_para(queryset, user_keywords, cond, k=30):
    same_para = []
    
    # Process each news item content
    for news in queryset:
        if not news.content:
            continue
            
        paragraphs = cut_paragraph(news.content)
        
        for para in paragraphs:
            para += "。"  # Add the period back
            
            if cond == 'and':
                if all([re.search(kw, para) for kw in user_keywords]):
                    same_para.append(para)
            elif cond == 'or':
                if any([re.search(kw, para) for kw in user_keywords]):
                    same_para.append(para)
                    
            # If we've got enough paragraphs, break out
            if len(same_para) >= k:
                break
                
    return same_para[:k]


print("app_user_keyword_association (DB version) was loaded!")
