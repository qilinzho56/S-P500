# PySimpleGUI referenced https://www.tutorialspoint.com/pysimplegui/index.htm
from sp500.headlines.scraper import headlines
import PySimpleGUI as sg
from sp500.time_series.visualization.company_profile import company_index_exhibit
from sp500.time_series.visualization.stock_movement import plot_stock_data_interactive
from sp500.time_series.visualization.best_model_viz import model_summary_figs, MODELS
from sp500.time_series.visualization.macro_indicators_viz import plot_macro_indicators
from sp500.time_series.time_series_preprocessing import test_train_prep
from sp500.time_series.price_model import rnd_best_params
import webbrowser
from pathlib import Path

FONT = {"Arial Bold", 16}
sg.set_options(font=FONT)


def create_row_layout(df, title):
    """
    Creates a layout for displaying a row of data from a Dataframe with each value 
    in an input field

    Parameters
    ----------
    df (Dataframe): company profile dataframe
    title (str): title displayed above the row of data

    Returns
    -------
    a list of lists as multiple rows in PySimpleGUI layout
    """
    headings = df.columns.tolist()
    values = df.iloc[0].tolist()
    layout = [[sg.Text(title, justification="center")]]

    for head, value in zip(headings, values):
        layout.append([sg.Text(f"{head}:"), sg.InputText(value, disabled=True)])

    return layout


def add_plots_and_tables_to_layout(plots, tables, base_dir):
    """
    Adds matplotlib plots and tables to a PySimpleGUI layout

    Parameters
    ----------
    plots (dict): mapping model types to a tuple with two figures
    tables (dict): mapping model types to a dataframe containing model evaluation metrics
    base_dir (pathlib.Path): the base directory where the plot will be saved

    Returns
    -------
    a list of lists as multiple rows in PySimpleGUI layout
    """
    layout = []

    for model_type, (fig1, fig2) in plots.items():
        fig1_path = base_dir / f"{model_type}_prediction_plot.png"
        fig2_path = base_dir / f"{model_type}_probability_plot.png"

        fig1.savefig(fig1_path)
        fig2.savefig(fig2_path)

        layout.append([sg.Text(f"{model_type} Prediction Vs Actual")])
        layout.append([sg.Image(filename=str(fig1_path))])

        layout.append([sg.Text(f"{model_type} Probability Distributions")])
        layout.append([sg.Image(filename=str(fig2_path))])

        table = tables[model_type]
        layout.append([sg.Text(f"{model_type} Summary of Metrics")])
        layout.append(
            [sg.Table(values=table.values.tolist(), headings=table.columns.tolist())]
        )

    return layout


def create_analysis_window(company):
    layout = [
        [sg.Text(f"Time-series analysis and prediction for {company}")],
        [
            sg.Button(
                "Click for sentiment analysis", key=f"SENTIMENT_ANALYSIS-{company}"
            )
        ],
    ]

    return sg.Window(f"Analysis for {company}", layout, modal=True)


def create_model_selection_window(company):
    model_selection_layout = [
        [sg.Text("Select a model for prediction:")],
        [sg.Combo(["ann", "rnf", "lstm"], default_value="ann", key="MODEL_SELECTION")],
        [sg.Button("Predict Tomorrow's Movement", key=f"PREDICT-{company}")],
    ]

    return model_selection_layout


class TickerApplication:
    def __init__(self):
        """
        Initialized the GUI with windows and parameters that need to be
        updated continuously.

        window1: user input tickers
        window2: news and URLs exhibit
        window3: company profile and stock movement plots
        window4: model evaluation, time-series analysis, and interactive guess
        window5: semantic analysis

        tickers: a list of user input tickers
        html_paths: a dictionary records live plotly image saved in html of each company
        company_data: a dictionary contains the preprocessed datasets as well as training/testing ones
        """
        self.tickers = []
        self.news_data = None
        self.window1()
        self.window2 = None
        self.window3 = None
        self.window4 = None
        self.html_paths = {}
        self.company_data = {}

    def window1(self):
        self.lst = sg.Listbox(
            self.tickers, size=(40, 6), expand_y=True, enable_events=True, key="-LIST-"
        )
        layout = [
            [
                sg.Input(size=(40, 6), expand_x=True, key="-INPUT-"),
                sg.Button("Add"),
                sg.Button("Remove"),
                sg.Button("Exit"),
            ],
            [
                sg.Text("Days to Look-up [same for all tickers]"),
                sg.Input(size=(40, 6), key="-Day-"),
            ],
            [self.lst],
            [sg.Text("", key="-MSG-", justification="center")],
            [sg.Submit()],
        ]
        self.window1 = sg.Window("Ticker Application", layout, size=(800, 400))

    def run_window1(self, headers):
        while True:
            event, values = self.window1.read()
            if event in (sg.WIN_CLOSED, "Exit"):
                break
            if event == "Add":
                self.tickers.append(values["-INPUT-"])
                self.window1["-LIST-"].update(self.tickers)
                msg = "A new ticker added : {}".format(values["-INPUT-"])
                self.window1["-MSG-"].update(msg)
            if event == "Remove":
                val = self.lst.get()[0]
                self.tickers.remove(val)
                self.window1["-LIST-"].update(self.tickers)
                msg = "A new ticker removed : {}".format(val)
                self.window1["-MSG-"].update(msg)
            if event == "Submit":
                company_list = self.tickers
                self.news_data = headlines(headers, company_list, int(values["-Day-"]))
                if self.news_data.empty:
                    msg = "Ticker Not Found/No Related News!"
                    self.window1["-MSG-"].update(msg)
                else:
                    msg = "Your News Report Has Been Fetched!"
                    self.window1["-MSG-"].update(msg)
                    self.update_window2()
                    self.run_window2()

        self.window1.close()

    def update_window2(self):
        headings = self.news_data.columns.tolist()
        self.data_overview = self.news_data.values.tolist()
        layout = [
            [
                sg.Table(
                    self.data_overview,
                    headings=headings,
                    size=(100, 100),
                    auto_size_columns=False,
                    col_widths=[5, 5, 7, 80, 10],
                    justification="left",
                    expand_x=True,
                    enable_events=True,
                    key="-TABLE-",
                ),
                sg.Button("For More Detailed Analysis"),
            ]
        ]

        self.window2 = sg.Window(
            "Overview with URLs Clickable", layout, size=(1400, 1000)
        )

    def run_window2(self):
        while True:
            event, values = self.window2.read()
            if event == sg.WIN_CLOSED:
                break

            if event == "-TABLE-":
                # First selected row
                row_clicked = values["-TABLE-"][0]
                url = self.data_overview[row_clicked][4]

                if url.startswith("https://"):
                    webbrowser.open(url)

            if event == "For More Detailed Analysis":
                self.update_window3()
                self.run_window3()

        self.window2.close()

    def update_window3(self):
        company_tabs = []

        for company in self.tickers:
            df1, df2, df3, df4, df5 = company_index_exhibit(company)

            company_overview_layout = create_row_layout(
                df1, f"{company} - Company Overview"
            )
            financial_performance_layout = create_row_layout(
                df2, f"{company} - Financial Performance"
            )
            cash_flow_layout = create_row_layout(df3, f"{company} - Cash Flow Analysis")
            profitability_efficiency_layout = create_row_layout(
                df4, f"{company} - Profitability Efficiency Analysis"
            )
            pe_metrics_layout = create_row_layout(df5, f"{company} - PE Metrics")

            img_byte, html_content = plot_stock_data_interactive(company)
            html_file_name = f"{company}_interactive_stock_plot.html"
            html_file_path = (
                Path(__file__).parents[1]
                / "time_series"
                / "visualization"
                / html_file_name
            )

            with open(html_file_path, "w") as html_file:
                html_file.write(html_content)

            self.html_paths[company] = f"file://{html_file_path.resolve()}"

            image_element = sg.Button(
                "Click to see dynamic graph!",
                image_data=img_byte,
                key=f"MOVEIMAGE-{company}",
                size=(22, 3),
                font=("Arial Bold", 15),
                button_color=("black", "white"),
            )

            graph_column = sg.Column([[image_element]], size=(1500, 900))

            tab_layout = [
                [
                    sg.Column(
                        company_overview_layout
                        + financial_performance_layout
                        + cash_flow_layout
                        + profitability_efficiency_layout
                        + pe_metrics_layout,
                        size=(400, 700),
                    ),
                    graph_column,
                ],
                [
                    sg.Button(
                        "Click for time-series analysis and prediction",
                        key=f"TIME_SERIES_ANALYSIS-{company}",
                    )
                ],
            ]

            company_tab = sg.Tab(company, tab_layout)
            company_tabs.append(company_tab)

        group_layout = [[sg.TabGroup([company_tabs], enable_events=True)]]

        self.window3 = sg.Window(
            "Company Data Overview", group_layout, size=(1800, 1000), finalize=True
        )

    def run_window3(self):
        while True:
            event, values = self.window3.read()
            if event == sg.WIN_CLOSED:
                break

            if isinstance(event, str):
                if event.startswith("MOVEIMAGE-"):
                    company = event.split("MOVEIMAGE-")[1]
                    html_file_path = self.html_paths.get(company)
                    if html_file_path:
                        webbrowser.open(html_file_path)

                if event.startswith("TIME_SERIES_ANALYSIS-"):
                    company = event.split("TIME_SERIES_ANALYSIS-")[1]
                    self.company_data[company] = test_train_prep(company)
                    self.update_window4(company)
                    self.run_window4()

        self.window3.close()

    def update_window4(self, company):
        data = self.company_data[company]
        preds_summary_plots, accuracy_tables = model_summary_figs(data, company, MODELS)
        base_dir = Path(__file__).parents[1] / "time_series" / "visualization"
        base_dir.mkdir(parents=True, exist_ok=True)

        macro_fig_path = base_dir / "Macro Indicators.png"

        model_selection_column = sg.Column(
            create_model_selection_window(company), vertical_alignment="top"
        )

        fig_table_layout = add_plots_and_tables_to_layout(
            preds_summary_plots, accuracy_tables, base_dir
        )
        fig_table_layout += [
            [sg.Text("Macroeconomic Index")],
            [sg.Image(filename=str(macro_fig_path))],
        ]

        scrollable_column = sg.Column(
            fig_table_layout,
            scrollable=True,
            vertical_scroll_only=True,
            size=(1000, 800),
        )

        top_layout = [[sg.Text(f"Time-series analysis and prediction for {company}")]]

        final_layout = (
            top_layout
            + [[model_selection_column]]
            + [[scrollable_column]]
            + [
                [
                    sg.Button(
                        "Click for sentiment analysis",
                        key=f"SENTIMENT_ANALYSIS-{company}",
                    )
                ]
            ]
        )

        self.window4 = sg.Window(
            f"Price-only Model Prediction Analysis for {company}",
            final_layout,
            size=(1200, 1000),
            resizable=True,
        )

    def run_window4(self):
        while True:
            event, values = self.window4.read()
            if event == sg.WIN_CLOSED:
                break

            if event.startswith("SENTIMENT_ANALYSIS-"):
                break

            if event.startswith("PREDICT-"):
                company = event.split("PREDICT-")[1]
                model_name = values["MODEL_SELECTION"]
                all_data, _, _, _, _ = self.company_data[company]
                if model_name == "lstm":
                    latest_sequence = all_data.iloc[-100:, :-1].to_numpy()
                    time_steps, features = latest_sequence.shape
                    latest_sequence_3d = latest_sequence.reshape(
                        1, time_steps, features
                    )
                    prediction = (
                        MODELS["lstm"].predict(latest_sequence_3d) > 0.5
                    ).astype(int)
                else:
                    prediction = MODELS[model_name].predict(
                        all_data.iloc[-1, :-1].values.reshape(1, -1)
                    )

                if prediction == 1:
                    sg.popup(f"Tomorrow's stock movement: Up by {model_name}")
                else:
                    sg.popup(f"Tomorrow's stock movement: Down by {model_name}")
