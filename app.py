import os
import gradio as gr
from crud import refresh_data, populate_dataframe
from db import PromoCode


SERVER_HOST = os.getenv('SERVER_HOST', 'localhost')
SERVER_PORT = int(os.getenv('SERVER_PORT', '80'))


data = populate_dataframe('UOTM Red Carpet')
headers = list(data[0].keys())
datatype = ['markdown' if '](' in str(v) else 'str' if type(v).__name__ == 'str' else 'number' for v in data[0].values()]
df_values = [list(row.values()) for row in data]

with gr.Blocks(fill_height=True) as INTERFACE:
    gr.Dataframe(
        value = df_values,
        headers = headers,
        datatype = datatype,
        row_count = len(data),
        col_count = len(headers),
        interactive = False,
    )
    # filter_dropdown = gr.Dropdown(choices=[pc.description for pc in PromoCode.get_all()])


if __name__ == '__main__':
    # refresh_data()
    INTERFACE.launch(server_name=SERVER_HOST, server_port=SERVER_PORT)

