import re
import os
from datetime import datetime
import plotly.graph_objects as go

def process_logs():
    fleet_data = {}
    log_file_path = 'raw_log.txt'
    
    if not os.path.exists(log_file_path):
        print("Error: raw_log.txt not found.")
        return

    serial_regex = re.compile(r"battery serial:([A-Za-z0-9]+)")
    cells_regex = re.compile(r"cell:([\d,\s]+)")

    with open(log_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("_line"):
                continue
            
            if '\t' not in line:
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
                
            raw_message = parts[0].strip()
            unix_ts_str = parts[1].strip()

            try:
                timestamp = datetime.fromtimestamp(int(unix_ts_str) / 1000.0)
            except Exception:
                continue

            serial_match = serial_regex.search(raw_message)
            cells_match = cells_regex.search(raw_message)

            if serial_match and cells_match:
                serial_name = serial_match.group(1).strip()
                cell_values = [int(v.strip()) for v in cells_match.group(1).split(',') if v.strip().isdigit()]

                if len(cell_values) != 10:
                    continue

                if serial_name not in fleet_data:
                    fleet_data[serial_name] = {
                        "timestamps": [],
                        **{f"Cell_{i+1}": [] for i in range(10)}
                    }

                fleet_data[serial_name]["timestamps"].append(timestamp)
                for i in range(10):
                    fleet_data[serial_name][f"Cell_{i+1}"].append(cell_values[i])

    charts_markup = []
    
    for serial, metrics in fleet_data.items():
        # Organize timelines chronologically
        combined = list(zip(metrics["timestamps"], *[metrics[f"Cell_{i+1}"] for i in range(10)]))
        combined.sort(key=lambda x: x[0])
        
        sorted_timestamps = [row[0] for row in combined]
        
        # Build an off-line responsive chart object using Python
        fig = go.Figure()
        
        for i in range(10):
            sorted_cell_voltages = [row[i+1] for row in combined]
            fig.add_trace(go.Scatter(
                x=sorted_timestamps,
                y=sorted_cell_voltages,
                mode='lines',
                name=f"Cell {i+1}"
            ))
            
        fig.update_layout(
            title='10-Cell Voltage Diagnostics Over Time',
            xaxis_title='Log Collection Time',
            yaxis_title='Voltage (mV)',
            template='plotly_white',
            margin=dict(t=50, b=50, l=60, r=30),
            hovermode='closest'
        )

        # Output the chart object as secure raw HTML code directly
        chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        card_html = f"""
        <div class="battery-card">
            <div class="battery-title">🔋 Battery Unit Serial: {serial}</div>
            <div style="width:100%;">
                {chart_html}
            </div>
        </div>
        """
        charts_markup.append(card_html)

    if not os.path.exists('templates/template.html'):
        print("Error: templates/template.html not found.")
        return

    with open('templates/template.html', 'r', encoding='utf-8') as file:
        template = file.read()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    final_output = template.replace('{{ update_time }}', now_str)
    final_output = final_output.replace('{{ battery_charts_html }}', "\n".join(charts_markup))

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_output)
    print(f"Successfully compiled vector visual blocks for {len(fleet_data)} hardware modules.")

if __name__ == '__main__':
    process_logs()
