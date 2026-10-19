import re
import os
import json
from datetime import datetime

def process_logs():
    fleet_data = {}
    log_file_path = 'raw_log.txt'
    
    if not os.path.exists(log_file_path):
        print("Error: raw_log.txt not found.")
        return

    # Regular expression blueprints adapted to find text patterns without string boundary issues
    serial_regex = re.compile(r"battery serial:([A-Za-z0-9]+)")
    cells_regex = re.compile(r"cell:([\d,\s]+)")

    with open(log_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("_line"): # Skip empty lines and the structural header row
                continue
            
            # Split the text statement from the trailing unix timestamp using the raw tab character (\t)
            if '\t' not in line:
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
                
            raw_message = parts[0].strip()
            unix_ts_str = parts[1].strip()

            # Convert millisecond timestamp string to calendar date strings safely
            try:
                timestamp = datetime.fromtimestamp(int(unix_ts_str) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                continue

            serial_match = serial_regex.search(raw_message)
            cells_match = cells_regex.search(raw_message)

            if serial_match and cells_match:
                serial_name = serial_match.group(1).strip()
                # Safely slice out the 10 internal cell voltages
                cell_values = [int(v.strip()) for v in cells_match.group(1).split(',') if v.strip().isdigit()]

                # Skip corrupted telemetry entries that don't match the 10-cell profile
                if len(cell_values) != 10:
                    continue

                # Dynamically append newly discovered batteries to our inventory dictionary
                if serial_name not in fleet_data:
                    fleet_data[serial_name] = {
                        "timestamps": [],
                        **{f"Cell {i+1}": [] for i in range(10)}
                    }

                fleet_data[serial_name]["timestamps"].append(timestamp)
                for i in range(10):
                    fleet_data[serial_name][f"Cell {i+1}"].append(cell_values[i])

    # Build individual Plotly visualization script objects 
    charts_markup = []
    
    for serial, metrics in fleet_data.items():
        # Zip data vectors together to force global sorting chronologically
        combined = list(zip(metrics["timestamps"], *[metrics[f"Cell {i+1}"] for i in range(10)]))
        combined.sort(key=lambda x: x[0]) # Sort records left-to-right by time string
        
        sorted_timestamps = [row[0] for row in combined]
        
        plotly_traces = []
        for i in range(10):
            sorted_cell_voltages = [row[i+1] for row in combined]
            trace_structure = {
                "x": sorted_timestamps,
                "y": sorted_cell_voltages,
                "mode": "lines",
                "name": f"Cell {i+1}"
            }
            plotly_traces.append(trace_structure)

        chart_id = f"chart_{serial}"
        card_html = f"""
        <div class="battery-card">
            <div class="battery-title">🔋 Battery Unit Serial: {serial}</div>
            <div id="{chart_id}" style="width:100%; height:450px;"></div>
            <script>
                var data_{chart_id} = {json.dumps(plotly_traces)};
                var layout_{chart_id} = {{
                    title: '10-Cell Voltage Diagnostics Over Time',
                    xaxis: {{ title: 'Log Collection Time', tickangle: -30 }},
                    yaxis: {{ title: 'Voltage (mV)', autorerange: true }},
                    margin: {{ t: 50, b: 100, l: 60, r: 30 }},
                    hovermode: 'closest'
                }};
                Plotly.newPlot('{chart_id}', data_{chart_id}, layout_{chart_id});
            </script>
        </div>
        """
        charts_markup.append(card_html)

    if not os.path.exists('templates/template.html'):
        print("Error: templates/template.html template blueprint file was missing.")
        return

    with open('templates/template.html', 'r', encoding='utf-8') as file:
        template = file.read()

    # Generate finished system webpage file
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    final_output = template.replace('{{ update_time }}', now_str)
    final_output = final_output.replace('{{ battery_charts_html }}', "\n".join(charts_markup))

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_output)
    print(f"Successfully generated dynamic visual panels for {len(fleet_data)} separate battery serial configurations.")

if __name__ == '__main__':
    process_logs()
