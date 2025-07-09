from pandas import read_csv,DataFrame,options,Series
options.display.float_format = '{:,.4f}'.format

def analyze_national_data():
    df:DataFrame = read_csv("National_Results - Copy.csv")
    
    df_states_mean:DataFrame = DataFrame(df.mean()).T
    df_states_mean.drop("Round",axis=1).to_csv("analysis/National_Results_Means.csv",index=False)
    df_states_mean.drop("Round",axis=1).to_html("analysis/National_Results_Means.html",index=False)
    
    df[(df["Republican Votes"] > df["Democrat Votes"])&(df["Republican Electoral Votes"] < df["Democrat Electoral Votes"])].to_html("analysis/Republican_Popular_Democrat_Electoral.html",index=False)
    df[(df["Republican Votes"] < df["Democrat Votes"])&(df["Republican Electoral Votes"] > df["Democrat Electoral Votes"])].to_html("analysis/Democrat_Popular_Republican_Electoral.html",index=False)


def analyze_state_data():
    df:DataFrame = read_csv("State_Results - Copy.csv")
    df_states_mean:DataFrame = df.groupby("State").mean(numeric_only=True)
    df_states_mean.insert(0, "State", sorted(df["State"].unique()))
    df_states_mean.drop(["Round","Electoral Votes"],axis=1).to_csv("analysis/State_Results_Means.csv",index=False)
    df_states_mean.drop(["Round","Electoral Votes"],axis=1).to_html("analysis/State_Results_Means.html",index=False)

    df.groupby(["State","Winner"]).count().reset_index(drop=False).to_html("analysis/State_Winners.html",index=True)

def main():
    analyze_national_data()
    analyze_state_data()

if __name__ == "__main__":
    main()