import pandas as pd
import requests
import json
import threading
from time import sleep
import time
from sqlalchemy import create_engine
import concurrent.futures
import configparser

def connect_MySQL():
    #MySQL connection information
    config=configparser.ConfigParser()
    config.read('config.ini')
    
    mysql_engine=create_engine(f"{config['MySQL']['driver']}://{config['MySQL']['username']}:{config['MySQL']['password']}@{config['MySQL']['host']}/{config['MySQL']['database']}") 
    return mysql_engine

def connect_AWSRedshift():
    #AWSRedshift connection information
    config=configparser.ConfigParser()
    config.read('config.ini')
  
    AWSRedshift_engine=create_engine(f"{config['AWSRedshift']['driver']}://{config['AWSRedshift']['username']}:{config['AWSRedshift']['password']}@{config['AWSRedshift']['host']}:{config['AWSRedshift']['port']}/{config['AWSRedshift']['database']}")
    return AWSRedshift_engine

def Get_List_ID(url):     
    response=requests.get(url,headers=headers,params=params)
    if response.status_code == 200:
        print(f'-------Crawl page {url[-1]} successfully!!!--------')
    for record in response.json().get('data'):
        product_list.append(record.get('id'))

def Get_Multi_Page():   
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(Get_List_ID,urls)

def Get_Product_Information(id):
    response=requests.get(f'https://tiki.vn/api/v2/products/{id}',headers=headers,params=params)
    text=response.content
    data=json.loads(text)

    master_={}
    productID=data['id']
    productName=data['name']
    brand=data['brand']['name']
    category=data['categories']['name']
    shopID=data['current_seller']['id']
    shopName=data['current_seller']['name']
    master_={
        'Product_ID':productID,
        'Product_Name':productName,
        'Brand':brand,
        'Category':category,
        'Shop_ID':shopID,
        'Shop_Name':shopName
    }
    masterProduct.append(master_)
    
    for i in range(0,len(data['configurable_products'])):
        detail_={}
        productID=data['id']
        SKU_ID=int(data['configurable_products'][i]['sku'])
        SKU_Name=data['configurable_products'][i]['option1']
        price=data['configurable_products'][i]['price']
        isActive_=data['configurable_products'][i]['inventory_status']
        if isActive_=="available":
            isActive=1
        else:
            isActive=0
        detail_={
            'Product_ID':productID,
            'SKU_ID':SKU_ID,
            'SKU_Name':SKU_Name,
            'Price':price,
            'Is_Active':isActive
        }
        productDetail.append(detail_)

    try: 
        soldItems=data['all_time_quantity_sold']
    except Exception as e:
        soldItems=''
        
    marketing_={}
    productID=data['id']
    countReviews=data['review_count']
    averageScore=data['rating_average']
    marketing_={
        'Product_ID':productID,
        'Count_Reviews':countReviews,
        'Average_Score':averageScore,
        'Sold_Items':soldItems
    }
    Marketing.append(marketing_)

def Get_Multi_Product():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(Get_Product_Information,product_list)

def Create_DataFrame():
    if masterProduct is not None:
        if productDetail is not None and Marketing is not None:
            print('------Data is available-------')
            
    df_MasterProduct=pd.DataFrame(data=masterProduct)
    df_ProductDetail=pd.DataFrame(data=productDetail)
    df_Marketing=pd.DataFrame(data=Marketing)
    
    
    # Dataframe to Excel 
    df_MasterProduct.to_excel('Master Product.xlsx')
    df_ProductDetail.to_excel('Product Detail.xlsx')
    df_Marketing.to_excel('Marketing.xlsx')
    print('-------Insert data to excel file successfully-------')
    #DataFrame to MySQL
    mysql_engine=connect_MySQL()
    df_MasterProduct.to_sql('master product',con=mysql_engine,if_exists='append',index=False)
    df_ProductDetail.to_sql('product detail',con=mysql_engine,if_exists='append',index=False)
    df_Marketing.to_sql('marketing',con=mysql_engine,if_exists='append',index=False)
    print('-------Insert data to MySQL successfully-------')
    
    # #DataFrame to AWS Redshift
    # redshift_engine=connect_AWSRedshift()
    # df_MasterProduct.to_sql('master product',con=redshift_engine,if_exists='append',index=False)
    # df_ProductDetail.to_sql('product detail',con=redshift_engine,if_exists='append',index=False)
    # df_Marketing.to_sql('marketing',con=redshift_engine,if_exists='append',index=False)
    # print('-------Insert data to AWS Redshift successfully-------')
    
    
if __name__ == "__main__":
    
    start_time=time.perf_counter()
    
    headers={
    'user-agent':'Mozilla/5.0 (iPad; CPU OS 13_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/87.0.4280.77 Mobile/15E148 Safari/604.1',
    'accept': 'application/json, text/plain, */*',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
    }

    params={
        'limit': '40',
        'include': 'advertisement',
        'is_mweb': '1',
        'aggregations': '2',
        'q': 'điện thoại samsung',
    }
    urls=[]
    temp_url=f'https://tiki.vn/api/v2/products?limit=40&include=advertisement&aggregations=2&q=%C4%91i%E1%BB%87n+tho%E1%BA%A1i+samsung&page='
    for i in range(1,5):
        url=temp_url+str(i)
        urls.append(url)
        
    product_list=[]
    masterProduct=[]
    productDetail=[]
    Marketing=[]
    
    Get_Multi_Page()
    Get_Multi_Product()
    Create_DataFrame()
    
    end_time=time.perf_counter()
    print('Executive time:',end_time-start_time)

    