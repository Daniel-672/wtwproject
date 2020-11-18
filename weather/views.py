from django.shortcuts import render, redirect, resolve_url
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Count, Sum
from datetime import datetime
import json
from bs4 import BeautifulSoup
import urllib.request as req
from bs4 import BeautifulSoup
import urllib.request as req
import pandas as pd
import datetime
import pymysql

# 오늘과 예측을 하기 위한 내일 날짜를 가져옴
def getweather(address):

    today = datetime.datetime.today().strftime('%Y%m%d')
    tomorrow = (datetime.datetime.today() + datetime.timedelta(days=1)).strftime('%Y%m%d')
    # print(today)
    # print(tomorrow)

    dicloc = {
        'address': ['서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시', '세종특별자치시', '경기도', '강원도', '충청북도',
                    '충청남도', '전라북도', '전라남도', '경상북도', '경상남도', '제주도'],
        'x': [60, 98, 89, 55, 58, 67, 102, 66, 60, 73, 69, 68, 63, 51, 89, 91, 52],
        'y': [127, 76, 90, 124, 74, 100, 84, 103, 120, 134, 107, 100, 89, 67, 91, 77, 38]}

    dfloc = pd.DataFrame(dicloc)
    xyloc = dfloc[dfloc['address'].isin([address])]

    # api = 'http://apis.data.go.kr/1360000/VilageFcstInfoService/getUltraSrtFcst?serviceKey=' #초단기예보
    api = 'http://apis.data.go.kr/1360000/VilageFcstInfoService/getVilageFcst?serviceKey='  # 동네예보
    key = '6TuB1szn0aNUEln7nrp6jgTQuv5WvoOgxRfPqdBtNPKTVIwbPV7SGmirrRyUIU95CP8oFZHn2f2Yr3zOWPiSdA%3D%3D'
    numOfRows = '1000'
    pageNo = '1'
    base_date = today
    base_time = '0200'
    # print(xyloc.iloc[0][1])
    # print(xyloc.iloc[0][2])

    nx = xyloc.iloc[0][1].astype('str')
    ny = xyloc.iloc[0][2].astype('str')

    savename = 'tmpweather.xml'

    url = api + key + '&numOfRows=' + \
          numOfRows + '&pageNo=' + pageNo + '&base_date=' + base_date + '&base_time=' + base_time + '&nx=' + nx + '&ny=' + ny

    req.urlretrieve(url, savename)

    xml = open(savename, 'r', encoding='utf-8').read()
    soup = BeautifulSoup(xml, 'xml')

    # print(soup.find_all('item'))

    weatherList = []
    for itemList in soup.find_all('item'):
        baseDate = itemList.find('baseDate').string
        baseTime = itemList.find('baseTime').string
        category = itemList.find('category').string
        fcstDate = itemList.find('fcstDate').string
        fcstTime = itemList.find('fcstTime').string
        fcstValue = itemList.find('fcstValue').string
        nx = itemList.find('nx').string
        ny = itemList.find('ny').string
        weatherList.append([baseDate, baseTime, category, fcstDate, fcstTime, fcstValue, nx, ny])

    df = pd.DataFrame(weatherList,
                      columns=['baseDate', 'baseTime', 'category', 'fcstDate', 'fcstTime', 'fcstValue', 'nx', 'ny'])

    df['ffcstValue'] = df['fcstValue'].astype('float')
    df_twoday = df[df['fcstDate'].isin([today, tomorrow])].groupby(['fcstDate', 'category']).mean(
        'fcstValue').reset_index()
    pv_towday = df_twoday.pivot(index=['fcstDate'], columns='category', values='ffcstValue').reset_index()
    pv_towday['temp_avg'] = pv_towday[['TMN', 'TMX']].mean(axis=1)
    pv_towday[['fcstDate', 'R06', 'REH', 'temp_avg']]

    returndic = {'today_rain': round(pv_towday[pv_towday['fcstDate'] == today].R06.values[0],1),
                 'today_humidity': round(pv_towday[pv_towday['fcstDate'] == today].REH.values[0],1),
                 'today_temp': round(pv_towday[pv_towday['fcstDate'] == today].temp_avg.values[0],1),
                 'today_ws': round(pv_towday[pv_towday['fcstDate'] == today].WSD.values[0],1),
                 'tomday_rain': round(pv_towday[pv_towday['fcstDate'] == tomorrow].R06.values[0],1),
                 'tomday_humidity': round(pv_towday[pv_towday['fcstDate'] == tomorrow].REH.values[0],1),
                 'tomday_temp': round(pv_towday[pv_towday['fcstDate'] == tomorrow].temp_avg.values[0],1),
                 'tomday_ws': round(pv_towday[pv_towday['fcstDate'] == tomorrow].WSD.values[0],1),
                 'address': address
                 }
    return returndic

# 주말로 bin만드는 함수 4:금 5:토 6:일 0:월
def get_week(dt):
    cat = ''
    if pd.to_datetime(dt).weekday() == 5:
        cat = 1
    elif pd.to_datetime(dt).weekday() == 6:
        cat = 1
    elif pd.to_datetime(dt).weekday() == 4:
        cat = 1
    elif pd.to_datetime(dt).weekday() == 0:
        cat = 1
    else:
        cat = 0
    return cat

# 네이버 쇼핑 회귀식에 의한 top5결과 추출
def getShopTop10Product(city='서울특별시'):
    # Rsquare를 추출
    conn = pymysql.connect(host='multi-bigdata.cljkqcsbb9ok.ap-northeast-2.rds.amazonaws.com', port=3306, user='edu02',
                           passwd='edu02', db='edudb01', cursorclass=pymysql.cursors.DictCursor)
    try:
        cur = conn.cursor()
        sql = '''
            SELECT *
            FROM Rsquare
            WHERE 1 = 1
        '''
        sql = sql + 'AND city = "' + city + '" '
        cur.execute(sql)
        result = cur.fetchall()
    finally:
        conn.close()
    dfProduct = pd.DataFrame(result)

    # 날씨를 추출
    addWeather = pd.DataFrame(getweather(city), index=[0])

    # 날씨와 Rsquare를 병합
    alldf = pd.merge(dfProduct, addWeather, left_on=["city"], right_on=["address"], how="inner")

    # weeksting과 bin을 만듬
    today = datetime.datetime.today()
    tomorrow = (datetime.datetime.today() + datetime.timedelta(days=1))

    # 주말처리 토일월과 그외 평일이면 wk0가 1 휴일이면 wk1이 1
    if get_week(today) == 0:  # 평일이면
        alldf['towk0'] = 1
        alldf['towk1'] = 0
    else:
        alldf['towk0'] = 0
        alldf['towk1'] = 1

    if get_week(today) == 0:  # 평일이면
        alldf['tomwk0'] = 1
        alldf['tomwk1'] = 0
    else:
        alldf['tomwk0'] = 0
        alldf['tomwk1'] = 1

    # 내일의 예상 클릭율
    alldf['xa2'] = alldf['xa'].apply(lambda x: x.replace('[', '').replace(']', '').split(','))
    alldf['b2'] = alldf['b'].apply(lambda x: x.replace('[', '').replace(']', '').split(','))

    # 내일의 예상 클릭율
    alldf['tomestV'] = alldf.apply(lambda x: round(float(x['xa2'][0]) * x['tomday_temp'] + float(x['xa2'][1]) * x['tomday_rain'] + float(x['xa2'][2]) * x['tomwk0'] + float(x['xa2'][3]) * x['tomwk1'] + float(x['b2'][0]), 1), axis=1)
    # 오늘의 예상 클릭율
    alldf['toestV'] = alldf.apply(lambda x: round(float(x['xa2'][0]) * x['today_temp'] + float(x['xa2'][1]) * x['today_rain'] + float(x['xa2'][2]) * x['towk0'] + float(x['xa2'][3]) * x['towk1'] + float(x['b2'][0]), 1), axis=1)

    alldf['incRate'] = alldf.apply(lambda x: round((x['tomestV'] - x['toestV']) / x['toestV'] * 100, 1), axis=1)

    returndf = alldf[['city', 'rsquare', 'response', 'toestV', 'tomestV', 'incRate']]

    #     top10 = lambda x: x.sort_values(by=['rsquare', 'incRate'], axis=0, ascending=False)[:6]
    #     resultdfbycity = returndf.groupby('city').apply(top10)

    returndf['absincRate'] = alldf.apply(lambda x: abs(x['incRate']), axis=1)
    # resultdfbycity = returndf.sort_values(by=['rsquare', 'incRate'], axis=0, ascending=False)[:6]
    resultdfbycity = returndf.sort_values(by='absincRate', axis=0, ascending=False)[:6]

    dicsum = resultdfbycity.to_dict('records')

    #     for x in dicsum:
    #         print(dicsum[x].values())

    return dicsum


# 예측가능한 6개도시 A형간염의 정보를 가져옴
def getTopDisea():
    # 예측가능한 5개도시 A형간염의 정보를 가져옴
    # def getTopDisea():
    city = ["경기도", "서울특별시", "대전광역시", "세종특별자치시", "인천광역시", "부산광역시", "울산광역시", "광주광역시", "대구광역시"]

    # Rsquare를 추출
    conn = pymysql.connect(host='multi-bigdata.cljkqcsbb9ok.ap-northeast-2.rds.amazonaws.com', port=3306, user='edu02',
                           passwd='edu02', db='edudb01', cursorclass=pymysql.cursors.DictCursor)
    try:
        cur = conn.cursor()
        sql = '''
            SELECT *
            FROM Rsquare_D
            WHERE 1 = 1
        '''
        cur.execute(sql)
        result = cur.fetchall()
    finally:
        conn.close()
    dfDiseas = pd.DataFrame(result)

    # 날씨를 추출
    addWeather = pd.DataFrame()
    for add in city:
        addWeather = addWeather.append(pd.DataFrame(getweather(add), index=[0]), ignore_index=True)

    # 질병과 Rsquare를 병합
    alldf = pd.merge(dfDiseas, addWeather, left_on=["city"], right_on=["address"], how="inner")
    # display(alldf)

    # weeksting과 bin을 만듬
    # ['temp_avg', 'amount_of_rain', 'r_humidity']
    today = datetime.datetime.today()
    tomorrow = (datetime.datetime.today() + datetime.timedelta(days=1))

    # 내일과 오늘의 예상 감염자수
    alldf['xa2'] = alldf['xa'].apply(lambda x: x.replace('[', '').replace(']', '').split(','))
    alldf['b2'] = alldf['b'].apply(lambda x: x.replace('[', '').replace(']', '').split(','))
    # display(alldf)

    # 내일의 예상 감염자수
    alldf['tomestV'] = alldf.apply(lambda x: round(
        float(x['xa2'][0]) * x['tomday_temp'] + float(x['xa2'][1]) * x['tomday_rain'] + float(x['xa2'][2]) * x[
            'tomday_humidity'] + float(x['b2'][0]), 1), axis=1)
    # 오늘의 예상 감염자수
    alldf['toestV'] = alldf.apply(lambda x: round(
        float(x['xa2'][0]) * x['today_temp'] + float(x['xa2'][1]) * x['today_rain'] + float(x['xa2'][2]) * x[
            'today_humidity'] + float(x['b2'][0]), 1), axis=1)

    # alldf['incRate'] = alldf.apply(lambda x: round((x['tomestV'] - x['toestV']) / x['toestV'] * 100, 1), axis=1)

    alldf['SUMtomestV'] = alldf['tomestV'].sum()

    alldf['piValue'] = alldf.apply(lambda x: round((x['tomestV'] / x['SUMtomestV']) * 100, 0), axis=1)

    returndf = alldf[['city', 'rsquare', 'response', 'toestV', 'tomestV', 'piValue']]

    returndic = {'paiCity': returndf['city'].tolist(),
                 'PaiValue': returndf['piValue'].tolist()
                 }

    return returndic


# 교통사고
def getAccidentCount(city='서울특별시'):
    pop = {
        'address': ['서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시',
                    '세종특별자치시', '경기도', '강원도', '충청북도', '충청남도', '전라북도', '전라남도',
                    '경상북도', '경상남도', '제주도'],
        'population': [9729107, 3413841, 2438031, 2957026, 1456468, 1474870, 1148019,
                       340575, 13239666, 1541502, 1600007, 2123709, 1818917, 1868745,
                       2665836, 3362553, 670989]
    }

    # 날씨를 추출
    addWeather = pd.DataFrame(getweather(city), index=[0])

    # 회귀식
    x = [0] * 22
    x[0] = addWeather['today_temp'][0]
    #     print(addWeather['today_temp'][0])
    if addWeather['today_rain'][0] < 1:
        x[1] = 1
    else:
        x[2] = 1
    x[3] = addWeather['today_ws'][0]
    x[4] = addWeather['today_humidity'][0]

    if addWeather['address'][0] == '강원도':
        x[5] = 1
    elif addWeather['address'][0] == '경기도':
        x[6] = 1
    elif addWeather['address'][0] == '경상남도':
        x[7] = 1
    elif addWeather['address'][0] == '경상북도':
        x[8] = 1
    elif addWeather['address'][0] == '광주광역시':
        x[9] = 1
    elif addWeather['address'][0] == '대구광역시':
        x[10] = 1
    elif addWeather['address'][0] == '대전광역시':
        x[11] = 1
    elif addWeather['address'][0] == '부산광역시':
        x[12] = 1
    elif addWeather['address'][0] == '서울특별시':
        x[13] = 1
    elif addWeather['address'][0] == '세종특별자치시':
        x[14] = 1
    elif addWeather['address'][0] == '울산광역시':
        x[15] = 1
    elif addWeather['address'][0] == '인천광역시':
        x[16] = 1
    elif addWeather['address'][0] == '전라남도':
        x[17] = 1
    elif addWeather['address'][0] == '전라북도':
        x[18] = 1
    elif addWeather['address'][0] == '제주도':
        x[19] = 1
    elif addWeather['address'][0] == '충청남도':
        x[20] = 1
    elif addWeather['address'][0] == '충청북도':
        x[21] = 1

    #     print(x)
    coef = [0.09551, -0.12152, 0.12152, -0.01190, 0.02075,
            -14.02573, 110.23470, -2.49813, 3.12397, -14.34688, 1.42490, -14.19731,
            -2.29574, 71.28671, -33.57688, -24.05782, -13.63816, -7.88631, -15.37370, -24.05272, -10.62914, -9.49175]
    #     print(len(coef))
    reg = sum([ix * c for ix, c in zip(x, coef)]) + 32.9931
    print(reg)
    p = pop['population'][pop['address'].index(city)]
    nreg = int(reg / p * 5000000)  # 인구500만명당
    reglist = {'reg1': nreg}

    return reglist

# 화재분석
def getFireCount(city):
    pop = {
        'address': ['서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시',
                    '세종특별자치시', '경기도', '강원도', '충청북도', '충청남도', '전라북도', '전라남도',
                    '경상북도', '경상남도', '제주도'],
        'population': [9729107, 3413841, 2438031, 2957026, 1456468, 1474870, 1148019,
                       340575, 13239666, 1541502, 1600007, 2123709, 1818917, 1868745,
                       2665836, 3362553, 670989]
    }

    # 날씨를 추출
    addWeather = pd.DataFrame(getweather(city), index=[0])

    # 회귀식
    x = [0] * 21
    x[0] = addWeather['today_temp'][0]
    #     print(addWeather['today_temp'][0])
    if addWeather['today_rain'][0] < 1:
        x[1] = 1
    else:
        x[2] = 1
    x[3] = addWeather['today_humidity'][0]

    if addWeather['address'][0] == '강원도':
        x[4] = 1
    elif addWeather['address'][0] == '경기도':
        x[5] = 1
    elif addWeather['address'][0] == '경상남도':
        x[6] = 1
    elif addWeather['address'][0] == '경상북도':
        x[7] = 1
    elif addWeather['address'][0] == '광주광역시':
        x[8] = 1
    elif addWeather['address'][0] == '대구광역시':
        x[9] = 1
    elif addWeather['address'][0] == '대전광역시':
        x[10] = 1
    elif addWeather['address'][0] == '부산광역시':
        x[11] = 1
    elif addWeather['address'][0] == '서울특별시':
        x[12] = 1
    elif addWeather['address'][0] == '세종특별자치시':
        x[13] = 1
    elif addWeather['address'][0] == '울산광역시':
        x[14] = 1
    elif addWeather['address'][0] == '인천광역시':
        x[15] = 1
    elif addWeather['address'][0] == '전라남도':
        x[16] = 1
    elif addWeather['address'][0] == '전라북도':
        x[17] = 1
    elif addWeather['address'][0] == '제주도':
        x[18] = 1
    elif addWeather['address'][0] == '충청남도':
        x[19] = 1
    elif addWeather['address'][0] == '충청북도':
        x[20] = 1

    #     print(len(x))
    coef = [0.00192, -0.10238, 0.10238, -0.11008,
            -1.05139, 19.52951, 2.94085, 0.17567, -4.17964, -3.64036, -3.90886, -0.46726,
            8.64716, -5.62294, -4.69020, -2.33327, 1.37958, -0.50270, -4.27094, 0.79168, -2.79691]
    #     print(len(coef))
    reg = sum([ix * c for ix, c in zip(x, coef)]) + 14.2178
    print(reg)
    p = pop['population'][pop['address'].index(city)]
    nreg = int(reg / p * 5000000)  # 인구 500만명당
    reglist = {'reg2': nreg}

    return reglist


# 농산물
def getGroceryPrice(grocery, city='서울특별시'):
    # 날씨를 추출
    addWeather = pd.DataFrame(getweather(city), index=[0])

    grodic = {'sweetpotato': [139.947, -38.055, -36.128, -33.362, -52.116, 159.661, 13.432, 5.833,
                              556.233, 474.477, -320.953, -21.544, -76.995, -306.520, -216.152, 180.931, 270.131,
                              -193.564, 186.870,
                              279.511, -60.291, -183.371, -751.221, 182.457, 3213.819],
              'chicken': [-2.994, -1.922, 23.859, 19.152, 1.916, -43.005, 11.216, 0.430,
                          443.526, 38.631, -788.754, 49.162, -164.614, 37.814, -479.543, -319.979, -404.456,
                          295.593, 140.186, -468.620, 128.872, -34.466, 1189.486, 337.165, 5109.417],
              'pork': [331.057, 103.304, -197.190, -39.575, 10.574, 122.887, 79.147, -11.807,
                       519.205, 422.362, 502.148, -355.289, -1131.132, -1740.791, -615.183, -2369.375,
                       -750.635, -981.832, 1293.090, 845.369, -766.357, 554.227, 2403.990, 2170.203, 16740.369],
              'beef': [388.166, 275.520, 316.127, -111.861, -538.034, 58.248, 54.042,
                       7.339, 6820.149, 5411.259, -2014.616, 2363.934, -3964.363, -7172.514, -813.339, -22376.518,
                       -6385.962, 7754.530, -19772.574, 10868.246, 15371.286, 9219.952, 9135.495, -4444.963, 92299.548],
              'cabbage': [118.818, 22.419, 29.150, -78.839, -310.664, 337.934, 248.780, 25.867, 785.066,
                          -54.638, -158.556, -163.478, 201.271, -35.139, -106.453, -372.349, 306.715, -1120.430,
                          199.912, 4.986, -612.587, -356.928, 822.362, 660.244, 1466.745],
              'spinach': [299.427, -412.135, -227.537, -494.958, -500.004, 1634.634, 349.496, 50.047,
                          696.817, 1248.684, -427.626, 269.766, 857.806, 863.712, -574.256, -259.661,
                          -156.257, 1826.959, 465.844, -2244.956, 279.794, -1077.360, -1199.571, -569.694, -138.575]}

    # 회귀식
    x = [0] * 24
    x[0] = addWeather['today_temp'][0]
    if addWeather['today_rain'][0] == 0:
        x[1] = 1
    elif addWeather['today_rain'][0] < 0.7:
        x[2] = 1
    elif addWeather['today_rain'][0] < 3.9:
        x[3] = 1
    elif addWeather['today_rain'][0] < 15.7:
        x[4] = 1
    else:
        x[5] = 1
    x[6] = addWeather['today_ws'][0]
    x[7] = addWeather['today_humidity'][0]

    if addWeather['address'][0] == '강원도':
        x[8] = 1
    elif addWeather['address'][0] == '경기도':
        x[9] = 1
    elif addWeather['address'][0] == '경상남도':
        x[10] = 1
    elif addWeather['address'][0] == '경상북도':
        x[11] = 1
    elif addWeather['address'][0] == '광주광역시':
        x[12] = 1
    elif addWeather['address'][0] == '대구광역시':
        x[13] = 1
    elif addWeather['address'][0] == '대전광역시':
        x[14] = 1
    elif addWeather['address'][0] == '부산광역시':
        x[15] = 1
    elif addWeather['address'][0] == '서울특별시':
        x[16] = 1
    elif addWeather['address'][0] == '세종특별자치시':
        x[17] = 1
    elif addWeather['address'][0] == '울산광역시':
        x[18] = 1
    elif addWeather['address'][0] == '인천광역시':
        x[19] = 1
    elif addWeather['address'][0] == '전라남도':
        x[20] = 1
    elif addWeather['address'][0] == '전라북도':
        x[21] = 1
    elif addWeather['address'][0] == '제주도':
        x[22] = 1
    elif addWeather['address'][0] == '충청북도':
        x[23] = 1

    #     print(len(grodic[grocery]))
    coef = grodic[grocery][:-1]
    #     print(coef)
    Y = grodic[grocery][-1:]
    #     print(Y)
    reg = sum([ix * c for ix, c in zip(x, coef)]) + Y
    #     print(reg)
    nreg = int(reg)
    reglist = {grocery: nreg}

    return reglist


def index(request):
    context = {
               }
    context.update(getweather('서울특별시'))
    context.update({'prodlist': getShopTop10Product('서울특별시')})
    context.update(getTopDisea())
    context.update(getAccidentCount('서울특별시'))
    context.update(getFireCount('서울특별시'))

    context.update(getGroceryPrice('sweetpotato','서울특별시'))
    context.update(getGroceryPrice('chicken', '서울특별시'))
    context.update(getGroceryPrice('pork', '서울특별시'))
    context.update(getGroceryPrice('beef', '서울특별시'))

    return render(request, 'index.html', context)


def chgaddress(request, add):
    context = {
               }
    context.update(getweather(add))
    context.update({'prodlist' : getShopTop10Product(add)})
    context.update(getTopDisea())
    context.update(getAccidentCount(add))
    context.update(getFireCount(add))

    context.update(getGroceryPrice('sweetpotato',add))
    context.update(getGroceryPrice('chicken', add))
    context.update(getGroceryPrice('pork', add))
    context.update(getGroceryPrice('beef', add))

    # context.update({'test': [10, 20, 30, 40, 50]})
#    print(context)
    return render(request, 'index.html', context)


def naver(request):
    context = {
               }
    return render(request, 'naver.html', context)
# Create your views here.
