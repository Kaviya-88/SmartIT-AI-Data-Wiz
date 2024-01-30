from flask import Flask,request,jsonify
from langchain.chat_models import ChatOpenAI
from chat2plot import chat2plot
# from langchain.agents import create_pandas_dataframe_agent
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
import os
from langchain.agents import AgentType
import pandas as pd
from dotenv import load_dotenv, find_dotenv
import openai


import re
import ast

_ = load_dotenv(find_dotenv())

app = Flask(__name__)


@app.route('/hello', methods = ["GET","POST"])
def home():
    return "hello world"


@app.route('/data-mapper', methods = ["GET","POST"])
def my_data():
    if request.method == "GET":
        sample_data ={
            'message':"Hello --- > Get Method",
            'data':[1,2,3,4]
        }
    if request.method == "POST":
        sample_data = {
            'message':"Hello --- > POST Method",
            'data':[5,6,7,8]
        }
    return jsonify(sample_data)


def data_agent():
    df = pd.read_excel("/Airline_main_data.xlsx")
    # openai.api_key = os.environ["OPENAI_API_KEY"]

    llm = ChatOpenAI(
        temperature=0, model="gpt-4", openai_api_key=os.environ["OPENAI_API_KEY"], streaming=True
    )
    c2p = chat2plot(df)
    pandas_df_agent = create_pandas_dataframe_agent(
        llm,
        df,
        verbose=True,
        prefix=""" 
                        You are working with a pandas dataframe in Python. The name of the dataframe is df.

                    If the query requires a table, format your answer like this:
                    {{"table": {{"columns": ["column1", "column2", ...], "data": [[value1, value2, ...], [value1, value2, ...], ...]}}},"answer":"your response goes here"}
                    
                    For a plain question that doesn't need a chart or table, your response should be:
                    {{"answer": "Your answer goes here"}}
                    
                    For example:
                    {{"answer": "The Product with the highest Orders is '15143Exfo'"}}
                    
                    If the answer is not known or available, respond with:
                    {{"answer": "I do not know."}}
                        """,

        agent_type=AgentType.OPENAI_FUNCTIONS,
        handle_parsing_errors=True,
    )
    return c2p, pandas_df_agent
    # chart_keyword = ["chart", "plot", "graph"]


@app.route('/start-analytics', methods = ["GET","POST"])
def analytics():
    plot_agent, pandas_agent = data_agent()
    query = request.args.get("query")
    if pandas_agent and plot_agent:
        if query:
            if "chart" in query:
                result = plot_agent(query)
                # response = type(result)

                labels_pattern = re.compile(r"'labels': array\((\[[^\]]+\])", re.DOTALL)
                values_pattern = re.compile(r"'values': array\((\[[^\]]+\])", re.DOTALL)
                hovertemplate_pattern = re.compile(r"'hovertemplate': '(.*?)'", re.DOTALL)
                hovertemplate_match = hovertemplate_pattern.search(str(result.figure))
                binning_count_pattern = re.compile(r'BINNING\((.*?),\s*1\)=\%{label}<br>COUNT\((.*?)\)=\%{value}')
                type_pattern = re.compile(r"'type': '(.*?)'", re.DOTALL)
                labels_match = labels_pattern.search(str(result.figure))
                values_match = values_pattern.search(str(result.figure))
                type_match = type_pattern.search(str(result.figure))
                binning_match = binning_count_pattern.search(hovertemplate_match.group(1))
                
                labels_array = ast.literal_eval(labels_match.group(1))
                type_value = type_match.group(1)
                values_list = ast.literal_eval(values_match.group(1))
                binning_value = binning_match.group(1)
                count_value = binning_match.group(2)

                result_dict = {
                    'labels': labels_array,
                    'type':type_value,
                    'values':values_list,
                    # "hover":hover_list
                    'columns': [binning_value, count_value],

                }
                response = {
                    "chart": result_dict,
                    "explanation":result.explanation
                }


                # response = {
                #             "explanation": result.explanation,
                #             "figure": str(result.figure),
                #             "config": str(result.config)
                #             }
                return jsonify(response)

            else:
                response = pandas_agent.run(query)
                return response
        else:
            return "query not received"

    elif pandas_agent:
        return "Pandas Agent Ready, Loading plot agent"
    else:
        return "Loading"


if __name__ == "__main__":
    app.run()
