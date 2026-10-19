import re
import os
import json
from datetime import datetime

def process_logs():
    # Structured dictionary: { battery_serial: { "timestamps": [], "cell_1": [], ... "cell_10": [] } }
    fleet_data = {}

    log_file_path = 'raw_log.txt'
    if not os.path.exists(log_file_path):
        print("Error: raw_log.txt not found.")
        return

    # Regular expression blueprints to parse your unstructured rows
    serial_regex = re.compile(r"battery serial:([A-Za-z0-9]+)")
    cells_regex = re.compile(r"cell:([\d,\s]+)")

    with open(log_file_path, 'r', encoding='utf-8') as file:
        for line in f:
            if not line.strip():
                continue
            
            # Extract the raw statement and trailing unix timestamp
            parts = line.rsplit(',', 1)
            if len(parts) < 2:
                continue
            
            raw_message = parts[0].strip('"')
            unix_ts_str = parts[1].strip()

            try:
                # Convert milliseconds timestamp to a readable datetime format
                timestamp = datetime.fromtimestamp(int(unix_ts_str) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue

            serial_match = serial_regex.search(raw_message)
            cells_match = cells_regex.search(raw_message)

            if serial_match and cells_match:
                serial_name = serial_match.group(1)
                # Split the comma-delimited cell data array
                cell_values = [int(v.strip()) for v in cells_match.group(1).split(',') if v.strip().isdigit()]
                
                # Verify telemetry integrity (ensure exactly 10 cell profiles)
                if len(cell_values) != 10:
                    continue

                # Initialize storage structures for freshly detected batteries dynamically
                if serial_name not in fleet_data:
                    fleet_data[serial_name] = {
                        "timestamps": [],
                        **{f"Cell {i+1}": [] for i in range(10)}
                    }

                fleet_data[serial_name]["timestamps"].append(timestamp)
                for i in range(10):
                    fleet_data[serial_name][f"Cell {i+1}"].append(cell_values[i])

    # Build Plotly JavaScript structures dynamically inside web cards
    charts_markup = []
    
    for serial, metrics in fleet_data.items():
        # Sort items chronologically by log timestamp
        combined = list(zip(metrics["timestamps"], *[metrics[f"Cell {i+1}"] for i in range(10)]))
        combined.sort(key=lambda x: x[0]) # sort by time
        
        sorted_timestamps = [row[0] for row in combined]
        
        # Build independent telemetry dataset lines
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

        # Output explicit component tags for individual diagnostic graphs
        chart_id = f"chart_{serial}"
        card_html = f"""
        <div class="battery-card">
            <div class="battery-title">🔋 Battery Unit: {serial}</div>
            <div id="{chart_id}" style="width:100%; height:450px;"></div>
            <script>
                var data_{chart_id} = {json.dumps(plotly_traces)};
                var layout_{chart_id} = {{
                    title: '10-Cell Voltage Diagnostics Over Time',
                    xaxis: {{ title: 'Log Collection Time', tickangle: -30 }},
                    yaxis: {{ title: 'Voltage (mV)' }},
                    margin: {{ t: 50, b: 100, l: 60, r: 30 }},
                    hovermode: 'closest'
                }};
                Plotly.newPlot('{chart_id}', data_{chart_id}, layout_{chart_id});
            </script>
        </div>
        """
        charts_markup.append(card_html)

    # Read layout file framework
    with open('templates/template.html', 'r', encoding='utf-8') as file:
        template = file.read()

    # Inject parsed calculations into dashboard asset variables
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    final_output = template.replace('{{ update_time }}', now_str)
    final_output = final_output.replace('{{ battery_charts_html }}', "\n".join(charts_markup))

    # Commit generated index layout to repo root directory for server presentation
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_output)
    print(f"Successfully generated visual logs dashboard for {len(fleet_data)} unique batteries.")

if __name__ == '__main__':
    process_logs()
