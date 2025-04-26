from django.shortcuts import render
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta

# (1) we can load data using read_csv()
# global variable
# df = pd.read_csv('dataset/news_dataset_preprocessed_for_django.csv', sep='|')

# (2) we can load data using reload_df_data() function
def load_df_data():
    # df is a global variable
    global  df
    df = pd.read_csv('app_user_keyword/dataset/cna_news_200_preprocessed.csv', sep='|')

# We should reload df when necessary
load_df_data() 

# hoem page
def home(request):
    return render(request, 'app_user_keyword/home.html')

# When POST is used, make this function be exempted from the csrf 
@csrf_exempt
def api_get_top_userkey(request):
    # (1) get keywords, category, condition, and weeks passed from frontend
    userkey = request.POST.get('userkey')
    cate = request.POST.get('cate')
    cond = request.POST.get('cond')
    weeks = int(request.POST.get('weeks'))
    key = userkey.split()
    
    # (2) make df_query global, so it can be used by other functions
    global  df_query 

    # (3) filter dataframe
    df_query = filter_dataFrame(key, cond, cate,weeks)
    #print(len(df_query))

    # (4) get frequency data
    key_freq_cat, key_occurrence_cat = count_keyword(df_query, key)
    print(key_occurrence_cat)
    
    # (5) get line chart data
    # key_time_freq = [
    # '{"x": "2019-03-07", "y": 2}',
    # '{"x": "2019-03-08", "y": 2}',
    # '{"x": "2019-03-09", "y": 13}']
    key_time_freq = get_keyword_time_based_freq(df_query)

    # (6) response all data to frontend home page
    response = {
    'key_occurrence_cat': key_occurrence_cat,
    'key_freq_cat': key_freq_cat,
    'key_time_freq': key_time_freq, }

    return JsonResponse(response)

def filter_dataFrame(user_keywords, cond, cate, weeks):

    # end date: the date of the latest record of news
    end_date = df.date.max()
    
    # start date
    start_date = (datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    # proceed filtering
    if (cate == "全部") & (cond == 'and'):
        query_df = df[(df.date >= start_date) & (df.date <= end_date) 
            & df.tokens_v2.apply(lambda text: all((qk in text) for qk in user_keywords))]
    elif (cate == "全部") & (cond == 'or'):
        query_df = df[(df['date'] >= start_date) & (df['date'] <= end_date) 
            & df.tokens_v2.apply(lambda text: any((qk in text) for qk in user_keywords))]
    elif (cond == 'and'):
        query_df = df[(df.category == cate) 
            & (df.date >= start_date) & (df.date <= end_date) 
            & df.tokens_v2.apply(lambda text: all((qk in text) for qk in user_keywords))]
    elif (cond == 'or'):
        query_df = df[(df.category == cate) 
            & (df['date'] >= start_date) & (df['date'] <= end_date) 
            & df.tokens_v2.apply(lambda text: any((qk in text) for qk in user_keywords))]
    return query_df


# ** How many pieces of news were the keyword(s) mentioned in?
# ** How many times were the keyword(s) mentioned?

# For the df_query, count the occurence and frequency for every category:
# (1) cate_occurence={}  number of pieces containing the keywords
# (2) cate_freq={}       number of times the keywords were mentioned

news_categories = ['全部','政治', '科技', '運動', '證卷', '產經', '娛樂', '生活', '國際', '社會', '文化', '兩岸']

def count_keyword(query_df, user_keywords):
    cate_occurence={}
    cate_freq={}

    for cate in news_categories:
        cate_occurence[cate]=0
        cate_freq[cate]=0

    for idx, row in query_df.iterrows():
        # count number of news
        cate_occurence[row.category] += 1
        cate_occurence['全部'] += 1
        
        # count user keyword frequency by checking every word in tokens_v2
        tokens = eval(row.tokens_v2)
        freq =  len([word for word in tokens if (word in user_keywords)])
        cate_freq[row.category] += freq
        cate_freq['全部'] += freq
        
    return cate_freq, cate_occurence

def get_keyword_time_based_freq(df_query):
    date_samples = df_query.date
    query_freq = pd.DataFrame({'date_index': pd.to_datetime(date_samples), 'freq': [1 for _ in range(len(df_query))]})
    data = query_freq.groupby(pd.Grouper(key='date_index', freq='D')).sum()
    time_data = []
    for i, idx in enumerate(data.index):
        row = {'x': idx.strftime('%Y-%m-%d'), 'y': int(data.iloc[i].freq)}
        time_data.append(row)
    return time_data

print("app_user_keyword was loaded!")
