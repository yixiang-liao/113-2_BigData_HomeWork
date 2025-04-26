from django.http import JsonResponse
from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt


# (1) Load news data--approach 1 直接指定某個csv檔案
def load_df_data_v1():
    global df # global variable
    # df = pd.read_csv('app_user_keyword/dataset/cna_news_200_preprocessed.csv',sep='|')
    df = pd.read_csv('app_user_keyword_sentiment/dataset/news_dataset_preprocessed_for_django.csv',sep='|')

# (2) Load news data--approach 2 跟隔壁的app借用df
# import from app_user_keyword.views and use df later
import app_user_keyword.views as userkeyword_views
def load_df_data():
    # import and use df from app_user_keyword 
    global df # global variable
    df = userkeyword_views.df

# call load data function when starting server
load_df_data_v1()
#load_df_data()

def home(request):
    return render(request, 'app_user_keyword_sentiment/home.html')

# GET: csrf_exempt is not necessary
# POST: csrf_exempt should be used
@csrf_exempt
def api_get_userkey_sentiment(request):

    userkey = request.POST['userkey']
    cate = request.POST['cate']
    cond = request.POST['cond']
    weeks = int(request.POST['weeks'])
    print(weeks)

    query_keywords = userkey.split()
    response = prepare_for_response(query_keywords, cond, cate, weeks)
  
    return JsonResponse(response)

def prepare_for_response(query_keywords, cond, cate, weeks):

    # Proceed filtering
    df_query = filter_df_via_content(query_keywords, cond, cate, weeks)
    
    sentiCount, sentiPercnt = get_article_sentiment(df_query)

    if weeks <= 4:
        freq_type = 'D'
    else:
        freq_type = 'W'

    line_data_pos = get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type=freq_type)
    line_data_neg = get_daily_basis_sentiment_count(df_query, sentiment_type='neg', freq_type=freq_type)

    response = {
        'sentiCount': sentiCount,
        'data_pos':line_data_pos,
        'data_neg':line_data_neg,
    }
    return response

def get_article_sentiment(df_query):
    sentiCount = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    sentiPercnt = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    numberOfArticle = len(df_query)
    for senti in df_query.sentiment:
        # determine sentimental polarity
        if float(senti) >= 0.6:
            sentiCount['Positive'] += 1
        elif float(senti) <= 0.4:
            sentiCount['Negative'] += 1
        else:
            sentiCount['Neutral'] += 1
    for polar in sentiCount :
        try:
            sentiPercnt[polar]=int(sentiCount[polar]/numberOfArticle*100)
        except:
            sentiPercnt[polar] = 0 # 若分母 numberOfArticle=0會報錯
    return sentiCount, sentiPercnt


def get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type='D'):

    # 自訂正負向中立的標準，sentiment score是機率值，介於0~1之間
    # Using lambda to determine if an article is postive or not.
    if sentiment_type == 'pos':
        lambda_function = lambda senti: 1 if senti >= 0.6 else 0 #大於0.6為正向 
    elif sentiment_type == 'neg':
        lambda_function = lambda senti: 1 if senti <= 0.4 else 0 #小於0.4為負向
    elif sentiment_type == 'neutral':
        lambda_function = lambda senti: 1 if senti > 0.4 & senti < 0.4 else 0 #介於中間為中立
    else:
        return None 
        
    freq_df = pd.DataFrame({'date_index': pd.to_datetime(df_query.date),
                             'frequency': [lambda_function(senti) for senti in df_query.sentiment]})
    # Group rows by the date to the daily number of articles. 加總合併同一天新聞，篇數就被計算好了
    freq_df_group = freq_df.groupby(pd.Grouper(key='date_index',freq=freq_type)).sum()
    
    # 'date_index'為index(索引)，將其變成欄位名稱，inplace=True表示原始檔案會被異動
    freq_df_group.reset_index(inplace=True)
    
    # x,y，用於畫趨勢線圖
    xy_line_data = [{'x':date.strftime('%Y-%m-%d'),'y':freq} for date, freq in zip(freq_df_group.date_index,freq_df_group.frequency)]
    return xy_line_data

# Searching keywords from "content" column
# Here this function uses df.content column, while filter_dataFrame() uses df.tokens_v2
def filter_df_via_content(query_keywords, cond, cate, weeks):

    # end date: the date of the latest record of news
    end_date = df.date.max()
    
    # start date
    start_date_delta = (datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
    start_date_min = df.date.min()
    # set start_date as the larger one from the start_date_delta and start_date_min 開始時間選資料最早時間與周數:兩者較晚者
    start_date = max(start_date_delta,   start_date_min)


    # (1) proceed filtering: a duration of a period of time
    # 期間條件
    period_condition = (df.date >= start_date) & (df.date <= end_date) 
    
    # (2) proceed filtering: news category
    # 新聞類別條件
    if (cate == "全部"):
        condition = period_condition  # "全部"類別不必過濾新聞種類
    else:
        # 過濾category新聞類別條件
        condition = period_condition & (df.category == cate)

    # (3) proceed filtering: and or
    # and or 條件
    if (cond == 'and'):
        # query keywords condition使用者輸入關鍵字條件and
        condition = condition & df.content.apply(lambda text: all((qk in text) for qk in query_keywords)) #寫法:all()
    elif (cond == 'or'):
        # query keywords condition使用者輸入關鍵字條件
        condition = condition & df.content.apply(lambda text: any((qk in text) for qk in query_keywords)) #寫法:any()
    # condiction is a list of True or False boolean value
    df_query = df[condition]

    return df_query


print("app_userkey_sentiment was loaded!")
