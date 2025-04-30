import requests
import json
import time
import random
from bs4 import BeautifulSoup

def fetch_sh_stocks():
    """获取上海证券交易所上市公司列表"""
    print("正在获取上海证券交易所股票...")
    stocks = {}
    
    # 上交所主板、科创板
    url = "http://www.sse.com.cn/assortment/stock/list/share/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": "http://www.sse.com.cn/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    }
    
    try:
        # 上交所主板数据
        response = requests.get("http://query.sse.com.cn/security/stock/getStockListData.do?stockType=1&pageHelp.beginPage=1&pageHelp.pageSize=2000", 
                                headers={
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                    "Referer": "http://www.sse.com.cn/assortment/stock/list/share/",
                                    "Accept": "application/json, text/javascript, */*; q=0.01"
                                })
        response.encoding = 'utf-8'
        data = response.json()
        
        for item in data.get('pageHelp', {}).get('data', []):
            stock_code = item.get('SECURITY_CODE_A', '')
            stock_name = item.get('SECURITY_ABBR_A', '')
            if stock_code and stock_name:
                stocks[stock_code] = stock_name
        
        # 科创板数据
        response = requests.get("http://query.sse.com.cn/security/stock/getStockListData.do?stockType=8&pageHelp.beginPage=1&pageHelp.pageSize=1000", 
                                headers={
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                    "Referer": "http://www.sse.com.cn/assortment/stock/list/share/",
                                    "Accept": "application/json, text/javascript, */*; q=0.01"
                                })
        response.encoding = 'utf-8'
        data = response.json()
        
        for item in data.get('pageHelp', {}).get('data', []):
            stock_code = item.get('SECURITY_CODE_A', '')
            stock_name = item.get('SECURITY_ABBR_A', '')
            if stock_code and stock_name:
                stocks[stock_code] = stock_name
                
        print(f"上海证券交易所股票获取成功，共 {len(stocks)} 只")
        return stocks
        
    except Exception as e:
        print(f"获取上交所数据出错: {e}")
        # 如果API请求失败，尝试备用方法：通过新浪接口获取
        return fetch_sh_stocks_from_sina()

def fetch_sh_stocks_from_sina():
    """通过新浪财经接口获取上交所股票列表（备用方法）"""
    stocks = {}
    try:
        # 获取上交所主板股票
        for prefix in ['60', '61', '68']:
            for i in range(10):
                base = f"{prefix}{i}00"
                url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=1000&sort=symbol&asc=1&node=sh{base}&symbol=&_s_r_a=init"
                
                response = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://vip.stock.finance.sina.com.cn/"
                })
                response.encoding = 'utf-8'
                
                if response.text.strip() and response.text != "null":
                    try:
                        data = json.loads(response.text)
                        for item in data:
                            code = item.get('symbol', '').replace('sh', '')
                            name = item.get('name', '')
                            if code and name:
                                stocks[code] = name
                    except:
                        pass
                
                time.sleep(0.5)  # 避免请求过快
    except Exception as e:
        print(f"通过新浪获取上交所数据出错: {e}")
    
    return stocks

def fetch_sz_stocks():
    """获取深圳证券交易所上市公司列表"""
    print("正在获取深圳证券交易所股票...")
    stocks = {}
    
    try:
        # 尝试从官方API获取
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "http://www.szse.cn/market/product/stock/list/index.html"
        }
        
        # 深交所主板
        response = requests.get(
            "http://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1110&TABKEY=tab1&random=" + str(random.random()),
            headers=headers
        )
        response.encoding = 'utf-8'
        
        try:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                for item in data[0].get('data', []):
                    code = item.get('agdm', '')  # 股票代码
                    name = item.get('agjc', '')  # 股票简称
                    if code and name:
                        stocks[code] = name
        except:
            pass
            
        # 中小板、创业板
        for board_type in ["tab2", "tab3"]:
            response = requests.get(
                f"http://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1110&TABKEY={board_type}&random=" + str(random.random()),
                headers=headers
            )
            response.encoding = 'utf-8'
            
            try:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    for item in data[0].get('data', []):
                        code = item.get('agdm', '')  # 股票代码
                        name = item.get('agjc', '')  # 股票简称
                        if code and name:
                            stocks[code] = name
            except:
                pass
            
            time.sleep(0.5)  # 避免请求过快
        
        if len(stocks) < 100:  # 如果获取数量太少，可能是接口问题，使用备用方法
            print("深交所官方API获取股票数量过少，切换到备用方法")
            return fetch_sz_stocks_from_sina()
            
        print(f"深圳证券交易所股票获取成功，共 {len(stocks)} 只")
        return stocks
        
    except Exception as e:
        print(f"获取深交所数据出错: {e}")
        # 备用方法
        return fetch_sz_stocks_from_sina()

def fetch_sz_stocks_from_sina():
    """通过新浪财经接口获取深交所股票列表（备用方法）"""
    stocks = {}
    try:
        # 获取深交所股票（主板、中小板、创业板）
        # 使用更全面的前缀列表，覆盖深交所所有股票类型
        for prefix in ['00', '30', '001', '002', '003', '004', '300', '301']:
            # 对每个前缀进行请求
            if len(prefix) == 2:
                # 两位前缀，尝试所有可能的第三位数字
                for i in range(10):
                    base = f"{prefix}{i}"
                    url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=1000&sort=symbol&asc=1&node=sz{base}&symbol=&_s_r_a=init"
                    
                    try:
                        response = requests.get(url, headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Referer": "http://vip.stock.finance.sina.com.cn/"
                        }, timeout=10)
                        response.encoding = 'utf-8'
                        
                        if response.text.strip() and response.text != "null":
                            try:
                                data = json.loads(response.text)
                                for item in data:
                                    code = item.get('symbol', '').replace('sz', '')
                                    name = item.get('name', '')
                                    if code and name:
                                        stocks[code] = name
                                print(f"获取到 {prefix}{i} 前缀股票 {len(data)} 只")
                            except Exception as e:
                                print(f"解析 {prefix}{i} 数据出错: {e}")
                    except Exception as e:
                        print(f"请求 {prefix}{i} 出错: {e}")
                        
                    time.sleep(0.2)  # 避免请求过快
            else:
                # 三位前缀，直接请求
                url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=1000&sort=symbol&asc=1&node=sz{prefix}&symbol=&_s_r_a=init"
                try:
                    response = requests.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "http://vip.stock.finance.sina.com.cn/"
                    }, timeout=10)
                    response.encoding = 'utf-8'
                    
                    if response.text.strip() and response.text != "null":
                        try:
                            data = json.loads(response.text)
                            for item in data:
                                code = item.get('symbol', '').replace('sz', '')
                                name = item.get('name', '')
                                if code and name:
                                    stocks[code] = name
                            print(f"获取到 {prefix} 前缀股票 {len(data)} 只")
                        except Exception as e:
                            print(f"解析 {prefix} 数据出错: {e}")
                except Exception as e:
                    print(f"请求 {prefix} 出错: {e}")
                    
                time.sleep(0.2)  # 避免请求过快
                
        # 尝试直接获取深交所板块分类的股票数据
        block_codes = ['sz_a', 'sz_b', 'sz_main', 'sz_zxb', 'sz_cyb']
        for block in block_codes:
            url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=2000&sort=symbol&asc=1&node={block}&symbol=&_s_r_a=init"
            try:
                response = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://vip.stock.finance.sina.com.cn/"
                }, timeout=10)
                response.encoding = 'utf-8'
                
                if response.text.strip() and response.text != "null":
                    try:
                        data = json.loads(response.text)
                        for item in data:
                            code = item.get('symbol', '').replace('sz', '')
                            name = item.get('name', '')
                            if code and name:
                                stocks[code] = name
                        print(f"获取到 {block} 板块股票 {len(data)} 只")
                    except Exception as e:
                        print(f"解析 {block} 数据出错: {e}")
            except Exception as e:
                print(f"请求 {block} 出错: {e}")
                
            time.sleep(0.2)  # 避免请求过快
                
        print(f"通过新浪获取深交所股票成功，共 {len(stocks)} 只")
    except Exception as e:
        print(f"通过新浪获取深交所数据出错: {e}")
    
    return stocks

def main():
    print("开始获取A股上市公司列表...")
    
    # 获取上交所股票
    sh_stocks = fetch_sh_stocks()
    
    # 获取深交所股票
    sz_stocks = fetch_sz_stocks()
    
    # 合并两个交易所的数据
    all_stocks = {**sh_stocks, **sz_stocks}
    
    # 按股票代码排序
    sorted_stocks = {k: all_stocks[k] for k in sorted(all_stocks.keys())}
    
    print(f"获取完成，共 {len(sorted_stocks)} 只股票")
    
    # 保存到JSON文件
    with open('stock_list.json', 'w', encoding='utf-8') as f:
        json.dump(sorted_stocks, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到 stock_list.json")

if __name__ == "__main__":
    main()
