import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import os

# -------------------------
# 1. 언어 선택 (기본: English)
# -------------------------
language = st.selectbox("Select Language / 언어 선택", ["English", "한국어"])

# -------------------------
# 2. 타이틀, 레이블, 개발자 정보 설정
# -------------------------
if language == "한국어":

    st.title("다중 종목 적립식 투자 시뮬레이터")
    tickers_label = "종목 티커 입력 (콤마로 구분, 예: SPY, AAPL, MSFT)"
    start_date_label = "시작 날짜"
    end_date_label = "종료 날짜"
    investment_label = "투자 금액 ($) (각 종목별)"
    period_label = "투자 주기 선택 (M: 매월, W-FRI: 매주 금요일, B: 매일)"
    period_options = ["M", "W-FRI", "B"]
    run_button = "시뮬레이션 실행"
    result_invested = "총 투자 금액"
    result_value = "최종 평가 금액"
    result_roi = "예상 수익률"
    result_drawdown = "최대 낙폭 (MDD)"
    chart_title = "종목별 및 전체 포트폴리오 결과"
    dev_info = "개발자: 변정식  |  이메일: dosmode111@gmail.com"
else:
    st.title("Multi-Stock Dollar-Cost Averaging Simulator")
    tickers_label = "Enter stock tickers (comma separated, e.g. SPY, AAPL, MSFT)"
    start_date_label = "Start Date"
    end_date_label = "End Date"
    investment_label = "Investment Amount ($) (per stock)"
    period_label = "Select Investment Period (M: Monthly, W-FRI: Weekly on Friday, B: Daily)"
    period_options = ["M", "W-FRI", "B"]
    run_button = "Run Simulation"
    result_invested = "Total Investment"
    result_value = "Final Portfolio Value"
    result_roi = "Estimated ROI"
    result_drawdown = "Maximum Drawdown (MDD)"
    chart_title = "Individual & Overall Portfolio Results"
    # 영어 개발자 정보에 이메일 추가
    dev_info = "Developer: Jungsik Jackson Byun  |  Email: dosmode111@gmail.com"

# 항상 표시되는 개발자 정보 (상단 또는 하단에 고정)
st.markdown("---")
st.markdown(f"**{dev_info}**")

# -------------------------
# 3. 사용자 입력
# -------------------------
tickers_input = st.text_input(tickers_label, "SPY, AAPL")
start_date = st.date_input(start_date_label, pd.to_datetime("2015-01-01"))
end_date = st.date_input(end_date_label, pd.to_datetime("2024-01-01"))
investment_amount = st.number_input(investment_label, min_value=0, value=500)
investment_period = st.selectbox(period_label, period_options, index=0)

# -------------------------
# 4. 한 종목 시뮬레이션 함수
# -------------------------
def simulate_stock(ticker, start_date, end_date, investment_amount, investment_period):
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="max")  # Fetch max available history

        if history.empty:
            raise ValueError("No data available")  # Handle nonexistent stocks

        first_available_date = history.index.min().strftime("%Y-%m-%d")

        # If requested start date is before the stock's IPO, adjust
        if start_date < first_available_date:
            error_msg = f"📉 {ticker}는 {first_available_date} 이후 데이터만 제공됩니다." if language == "한국어" else f"📉 {ticker} only has data from {first_available_date} onwards."
            st.warning(error_msg)
            return None

        df_raw = stock.history(start=start_date, end=end_date)

        if df_raw.empty:
            error_msg = f"❌ {ticker}의 데이터를 가져올 수 없습니다." if language == "한국어" else f"❌ Failed to fetch data for {ticker}."
            st.warning(error_msg)
            return None

        # Select the 'Close' price column
        close_col = "Close" if "Close" in df_raw.columns else "Adj Close"
        df = df_raw[[close_col]].copy().ffill()

        # Investment logic
        invest_dates = df.resample({'M': 'ME', 'W-FRI': 'W-FRI', 'B': 'B'}.get(investment_period, 'B')).first().index
        invest_dates = invest_dates[invest_dates.isin(df.index)]

        df["Investment"] = 0
        df.loc[invest_dates, "Investment"] = investment_amount
        df["Shares Purchased"] = df["Investment"] / df[close_col]
        df["Total Shares"] = df["Shares Purchased"].cumsum()
        df["Portfolio Value"] = df["Total Shares"] * df[close_col]
        df["Portfolio Max"] = df["Portfolio Value"].cummax()
        df["Drawdown"] = df["Portfolio Value"] / df["Portfolio Max"] - 1
        df["Cumulative Investment"] = df["Investment"].cumsum()

        return df

    except Exception as e:
        error_msg = f"⚠️ 오류 발생: {str(e)}" if language == "한국어" else f"⚠️ Error occurred: {str(e)}"
        st.error(error_msg)
        return None


# -------------------------
# 5. 시뮬레이션 실행 및 결과 처리 (다중 종목)
# -------------------------
if st.button(run_button):
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    results = {}
    overall_indices = set()
    for t in tickers:
        sim_df = simulate_stock(t, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), investment_amount, investment_period)
        if sim_df is None:
            st.error(f"❌ {t} 데이터를 불러올 수 없습니다.")
        else:
            results[t] = sim_df
            overall_indices.update(sim_df.index)
    
    if not results:
        st.error("❌ 모든 종목의 데이터를 불러올 수 없습니다.")
        st.stop()
    
    # 전체 포트폴리오 결과 계산
    overall_index = pd.to_datetime(sorted(overall_indices))
    overall_df = pd.DataFrame(index=overall_index)
    
    # 각 종목의 Investment와 Portfolio Value를 reindex (결측치는 0)
    for t, sim_df in results.items():
        temp = sim_df[["Investment", "Portfolio Value"]].reindex(overall_index, fill_value=0)
        temp.columns = [f"{t}_Investment", f"{t}_Value"]
        overall_df = overall_df.join(temp, how="outer")
    
    overall_df = overall_df.fillna(0)
    
    # 전체 일자별 투자액: 각 종목의 Investment (투자한 날에만 값이 있으므로)
    overall_df["Overall Daily Investment"] = overall_df[[col for col in overall_df.columns if "Investment" in col]].sum(axis=1)
    # 누적 투자액은 실제 투자한 날의 합산 (forward fill 대신 cumsum)
    overall_df["Overall Investment"] = overall_df["Overall Daily Investment"].cumsum()
    
    # 전체 Portfolio Value는 각 종목의 Portfolio Value의 합산
    overall_df["Overall Value"] = overall_df[[col for col in overall_df.columns if "Value" in col]].sum(axis=1)
    overall_df["Overall Portfolio Max"] = overall_df["Overall Value"].cummax()
    overall_df["Overall Drawdown"] = overall_df["Overall Value"] / overall_df["Overall Portfolio Max"] - 1
    
    # -------------------------
    # 6. 개별 종목 결과 표시
    # -------------------------
    st.markdown("## " + ("Individual Stock Results" if language=="English" else "개별 종목 결과"))
    for t, sim_df in results.items():
        final_value = sim_df["Portfolio Value"].iloc[-1]
        total_invested = sim_df["Investment"].sum()
        roi = (final_value / total_invested - 1) * 100 if total_invested != 0 else 0
        st.markdown(f"### {t}")
        st.write(f"**{result_invested}:** ${total_invested:,.2f}")
        st.write(f"**{result_value}:** ${final_value:,.2f}")
        st.write(f"**{result_roi}:** {roi:.2f}%")
    
    # -------------------------
    # 7. 전체 포트폴리오 결과 표시
    # -------------------------
    st.markdown("## " + ("Overall Portfolio Results" if language=="English" else "전체 포트폴리오 결과"))
    
    # 그래프 설정 - 언어에 따라 폰트 설정 (한국어 선택 시 한글 폰트 적용)
    if language == "한국어":
        import matplotlib.font_manager as fm
        import os
        font_path = os.path.join(os.path.dirname(__file__), "NanumGothicCoding.ttf")
        if not os.path.exists(font_path):
            print(f"폰트 파일을 찾을 수 없습니다: {font_path}")
        else:
            print("폰트 파일이 존재합니다:", font_path)
        font_path = os.path.join(os.path.dirname(__file__), "NanumGothicCoding.ttf")
 # 폰트 파일이 app.py와 같은 디렉터리에 있어야 합니다.
        try:
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            font_name = font_prop.get_name()
            print("실제 폰트 이름:", font_name)
            plt.rcParams['font.family'] = font_prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
        except Exception as e:
            st.warning("한국어 폰트 적용에 실패했습니다. 기본 폰트가 사용됩니다.")
    else:
        plt.rcParams['font.family'] = "sans-serif"
        plt.rcParams['axes.unicode_minus'] = False
    
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.plot(overall_df.index, overall_df["Overall Value"], label=("Overall Portfolio Value" if language=="English" else "전체 포트폴리오 평가 금액"), color="blue")
    ax2.plot(overall_df.index, overall_df["Overall Investment"], label=("Overall Cumulative Investment" if language=="English" else "전체 누적 투자 금액"), color="red", linestyle="dashed")
    ax2.fill_between(overall_df.index, overall_df["Overall Value"], overall_df["Overall Portfolio Max"],
                     color="red", alpha=0.3, label=("Overall Max Drawdown" if language=="English" else "전체 최대 낙폭"))
    ax2.set_title(chart_title + " (Overall Portfolio)")
    ax2.set_xlabel("Date" if language=="English" else "날짜")
    ax2.set_ylabel("Amount ($)" if language=="English" else "금액 ($)")
    ax2.legend()
    ax2.grid(True)
    st.pyplot(fig2)
    
    final_overall_value = overall_df["Overall Value"].iloc[-1]
    total_overall_investment = overall_df["Overall Investment"].iloc[-1]
    overall_roi = (final_overall_value / total_overall_investment - 1) * 100 if total_overall_investment != 0 else 0
    overall_max_drawdown = overall_df["Overall Drawdown"].min()
    
    st.write(f"**{result_invested}:** ${total_overall_investment:,.2f}")
    st.write(f"**{result_value}:** ${final_overall_value:,.2f}")
    st.write(f"**{result_roi}:** {overall_roi:.2f}%")
    st.write(f"**{result_drawdown}:** {overall_max_drawdown:.2%}")
