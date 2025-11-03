import datetime
import yfinance as yf
import pandas as pd
import time

def screen_stocks(market_cap_min=10e9, sector=None, eps_min=1, throttle_sec=1.0):
    """
    通过yfinance筛选符合条件的股票，简化示例，仅用市值和行业过滤
    """
    # 这里用一个简单清单演示，真实可扩展为API调用批量筛选
    tickers = ['AAPL', 'TSLA', 'NVDA', 'AMZN', 'MSFT']
    selected = []
    # 避免 429：不再调用 get_info()，如用户传入 sector/eps_min，则提示忽略
    if sector is not None or (eps_min is not None and eps_min != 1):
        print("[提示] 由于Yahoo Finance接口限流，已忽略 sector/eps 过滤条件，仅按市值筛选。")
    for ticker in tickers:
        # 简单节流+抖动，降低 429 概率
        if throttle_sec and throttle_sec > 0:
            jitter = throttle_sec * 0.25
            time.sleep(throttle_sec + (jitter))
        stock = yf.Ticker(ticker)
        # 使用更可靠的 fast_info 获取市值；加上指数退避避免 429
        market_cap = None
        retries = 3
        backoff = 1.0
        for attempt in range(retries):
            try:
                fi = stock.fast_info  # 字典, 包含 'market_cap' 等字段
                market_cap = fi.get('market_cap')
                # 如无 market_cap，尝试用价格 * 流通股 (若可得)
                if market_cap is None:
                    last_price = fi.get('last_price') or fi.get('regular_market_previous_close')
                    shares = fi.get('shares_outstanding') or fi.get('shares')
                    if last_price is not None and shares is not None:
                        market_cap = float(last_price) * float(shares)
                break
            except Exception as e:
                # 简单退避处理 Too Many Requests
                if attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    market_cap = None

        # 过滤逻辑：
        # - 若取不到市值，则跳过该ticker
        # - sector/eps 过滤被禁用以避免触发限流
        if market_cap is None:
            continue
        if market_cap >= market_cap_min:
            selected.append(ticker)
    return selected

def get_leaps_calls(ticker, min_expiration_months=12, atm_strike_spread=0.1, throttle_sec=0.5, max_expirations=4):
    """
    获取ticker的LEAPS看涨期权，筛选到期时间超过X个月，行权价接近现价±10%
    返回DataFrame包含合约信息
    """
    stock = yf.Ticker(ticker)
    # 获取当前价，优先用 fast_info, 失败时回退到 history
    current_price = None
    try:
        fi = stock.fast_info
        current_price = fi.get('last_price') or fi.get('regular_market_previous_close')
    except Exception:
        current_price = None
    if current_price is None:
        try:
            current_price = stock.history(period='1d')['Close'].iloc[-1]
        except Exception:
            return pd.DataFrame()
    
    leaps_calls = []
    try:
        options_dates = stock.options
    except Exception:
        options_dates = []
    # 只查询前若干个满足期限的到期日，减少请求次数
    filtered_dates = []
    for exp_date in options_dates:
        try:
            expiration = datetime.datetime.strptime(exp_date, "%Y-%m-%d")
            months_to_expiry = (expiration.year - datetime.datetime.now().year) * 12 + expiration.month - datetime.datetime.now().month
            if months_to_expiry >= min_expiration_months:
                filtered_dates.append((exp_date, months_to_expiry))
        except Exception:
            continue
    # 按离现在最近到最远排序，最多取 max_expirations 个
    filtered_dates.sort(key=lambda x: x[1])
    for exp_date, _ in filtered_dates[:max_expirations]:
        try:
            if throttle_sec and throttle_sec > 0:
                time.sleep(throttle_sec)
            opt_chain = stock.option_chain(exp_date)
            calls = opt_chain.calls
            # 选取行权价在当前价格附近的看涨期权
            strikes_filter = calls[(calls['strike'] >= current_price * (1 - atm_strike_spread)) & 
                                  (calls['strike'] <= current_price * (1 + atm_strike_spread))]
            if not strikes_filter.empty:
                # 添加 expiration 列便于后续展示
                strikes_filter = strikes_filter.copy()
                strikes_filter['expiration'] = exp_date
                leaps_calls.append(strikes_filter)
        except Exception:
            continue
    if leaps_calls:
        return pd.concat(leaps_calls)
    else:
        return pd.DataFrame()

def main():
    # 1. 筛选符合条件的股票（例如科技行业，高市值）
    stocks = screen_stocks(market_cap_min=10e9, sector='Technology', eps_min=2, throttle_sec=1.0)
    print(f"筛选股票: {stocks}")
    
    # 2. 对筛选出的每只股票，获取并展示其LEAPS看涨期权合约
    for ticker in stocks:
        leaps = get_leaps_calls(ticker, throttle_sec=0.5, max_expirations=3)
        if not leaps.empty:
            print(f"\n{ticker} 的 LEAPS Call Options (行权价接近现价±10%, 到期≥12个月):")
            print(leaps[['contractSymbol', 'strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'expiration']])
        else:
            print(f"\n{ticker} 没有符合LEAPS条件的期权。")

if __name__ == "__main__":
    main()
