import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# =======================
# 1. 기본 설정 및 다국어 지원
# =======================
language = st.selectbox("언어 선택 / Select Language", ["한국어", "English"])

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
    dev_info = "Developer: Jungsik Jackson Byun"

# 항상 개발자 정보 표시 (버튼과 상관없이)
st.markdown("---")
st.markdown(f"**{dev_info}**")

# =======================
# 2. 사용자 입력
# =======================
tickers_input = st.text_input(tickers_label, "SPY, AAPL")
start_date = st.date_input(start_date_label, pd.to_datetime("2015-01-01"))
end_date = st.date_input(end_date_label, pd.to_datetime("2024-01-01"))
investment_amount = st.number_input(investment_label, min_value=0, value=500)
investment_period = st.selectbox(period_label, period_options, index=0)

# =======================
# 3. 시뮬레이션 함수 정의 (한 종목)
# =======================
def simulate_stock(ticker, start_date, end_date, investment_amount, investment_period):
    df_raw = yf.download(ticker, start=start_date, end=end_date)
    if df_raw.empty:
        return None
    # 사용할 열 선택: 'Close' 또는 'Adj Close'
    if "Close" in df_raw.columns:
        close_col = "Close"
    elif "Adj Close" in df_raw.columns:
        close_col = "Adj Close"
    else:
        return None
    # 'Close' 열만 사용하고 결측값 보정
    df = df_raw[[close_col]].copy()
    df = df.ffill()
    # 단일 열 DataFrame를 Series로 변환 후, 다시 DataFrame으로 재구성
    close_series = df[close_col].squeeze()  # Series
    df = pd.DataFrame({close_col: close_series})
    
    # 투자 날짜 선정
    if investment_period == "M":
        invest_dates = df.resample('ME').first().index  # 월말 기준
    elif investment_period == "W-FRI":
        invest_dates = df.resample('W-FRI').first().index
    elif investment_period == "B":
        invest_dates = df.index  # 모든 영업일
    else:
        invest_dates = df.index
    invest_dates = invest_dates[invest_dates.isin(df.index)]
    
    # Investment 컬럼 생성 (해당 날짜에만 투자금액 부여)
    df["Investment"] = 0
    df.loc[invest_dates, "Investment"] = investment_amount
    df["Investment"] = df["Investment"].fillna(0)
    
    # 구매한 주식 수 = Investment / Close
    df["Shares Purchased"] = (df["Investment"] / df[close_col]).fillna(0)
    # 누적 주식 수
    df["Total Shares"] = df["Shares Purchased"].cumsum()
    # 포트폴리오 가치 = 누적 주식 수 * Close
    df["Portfolio Value"] = (df["Total Shares"] * df[close_col]).fillna(0)
    
    df["Portfolio Max"] = df["Portfolio Value"].cummax()
    df["Drawdown"] = df["Portfolio Value"] / df["Portfolio Max"] - 1
    df["Cumulative Investment"] = df["Investment"].cumsum()
    
    return df

# =======================
# 4. 시뮬레이션 실행 및 결과 처리
# =======================
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
    
    # 각 종목별 투자액과 평가 금액을 전체 DataFrame에 reindex (missing 값은 0으로 채우기)
    for t, sim_df in results.items():
        temp = sim_df[["Investment", "Portfolio Value"]].reindex(overall_index, fill_value=0)
        temp.columns = [f"{t}_Investment", f"{t}_Value"]
        overall_df = overall_df.join(temp, how="outer")
    
    overall_df = overall_df.fillna(0)
    
    # 전체 일자별 투자액은 각 종목의 Investment(실제 투자한 날만 값이 있고, 나머지는 0)
    overall_df["Overall Daily Investment"] = overall_df[[col for col in overall_df.columns if "Investment" in col]].sum(axis=1)
    # 누적 투자액 = 일자별 투자액의 누적 합계 (forward fill하지 않고, 실제 투자한 날의 합산)
    overall_df["Overall Investment"] = overall_df["Overall Daily Investment"].cumsum()
    
    # 전체 Portfolio Value = 각 종목의 Portfolio Value의 합산 (forward fill 필요 없음)
    overall_df["Overall Value"] = overall_df[[col for col in overall_df.columns if "Value" in col]].sum(axis=1)
    overall_df["Overall Portfolio Max"] = overall_df["Overall Value"].cummax()
    overall_df["Overall Drawdown"] = overall_df["Overall Value"] / overall_df["Overall Portfolio Max"] - 1
    
    # =======================
    # 5. 개별 종목 결과 표시
    # =======================
    st.markdown("## 개별 종목 결과" if language=="한국어" else "## Individual Stock Results")
    for t, sim_df in results.items():
        final_value = sim_df["Portfolio Value"].iloc[-1]
        total_invested = sim_df["Investment"].sum()
        roi = (final_value / total_invested - 1) * 100 if total_invested != 0 else 0
        st.markdown(f"### {t}")
        st.write(f"**{result_invested}:** ${total_invested:,.2f}")
        st.write(f"**{result_value}:** ${final_value:,.2f}")
        st.write(f"**{result_roi}:** {roi:.2f}%")
    
    # =======================
    # 6. 전체 포트폴리오 결과 표시
    # =======================
    st.markdown("## 전체 포트폴리오 결과" if language=="한국어" else "## Overall Portfolio Results")
    
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.plot(overall_df.index, overall_df["Overall Value"], label="전체 포트폴리오 평가 금액" if language=="한국어" else "Overall Portfolio Value", color="blue")
    ax2.plot(overall_df.index, overall_df["Overall Investment"], label="전체 누적 투자 금액" if language=="한국어" else "Overall Cumulative Investment", color="red", linestyle="dashed")
    ax2.fill_between(overall_df.index, overall_df["Overall Value"], overall_df["Overall Portfolio Max"],
                     color="red", alpha=0.3, label="전체 최대 낙폭" if language=="한국어" else "Overall Max Drawdown")
    ax2.set_title(chart_title + " (전체 포트폴리오)")
    ax2.set_xlabel("날짜" if language=="한국어" else "Date")
    ax2.set_ylabel("금액 ($)" if language=="한국어" else "Amount ($)")
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
