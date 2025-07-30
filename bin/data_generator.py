import os
import csv
import random
from datetime import datetime, timedelta

# Configurable parameters - Scale up to thousands of hosts
hosts = ["host-01"]  # 1 host
interval_minutes = 5
days = 365  # Simulate for 1 year
start_time = datetime.now() - timedelta(days=days)
points_per_host = (24 * 60 // interval_minutes) * days
rows_count = 0

print(f"Generating data for {len(hosts)} hosts over {days} days...")
print(f"Total data points: {len(hosts) * points_per_host:,}")

# Function to inject anomalies
def get_anomaly_indexes():
    """Select random indexes for anomaly injection in the time series."""
    indexes = random.sample(
        range(50, points_per_host - 50), k=random.randint(2, 4)
    )  # 2-4 anomalies per host
    return set(indexes)


# Function to generate monitoring data with anomalies
def generate_row(timestamp, host, index, rows_count):
    """Generate a row of monitoring data (with anomalies at specific indexes)."""
    is_anomaly = index in host_anomalies[host]

    if is_anomaly:
        # Inject anomalies
        cpu_usage = round(random.uniform(90, 100), 2)  # High CPU usage for anomaly
        anomalies.append((timestamp.strftime("%Y-%m-%d %H:%M:%S"), host))
    else:
        # Normal behavior
        cpu_usage = round(random.gauss(25, 8), 2)

    return {
        "ID": rows_count,
        "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "Host": host,
        "CPU Usage": cpu_usage,
    }

# Generate synthetic data and write to CSV
def generate_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    os.makedirs(data_dir, exist_ok=True)
    output_file = os.path.join(data_dir, "mock_zabbix_data.csv")
    
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ID",
                "Timestamp",
                "Host",
                "CPU Usage",
            ],
        )
        writer.writeheader()

        total_points = len(hosts) * points_per_host
        current_time = start_time
        for i in range(total_points):
            global rows_count
            rows_count += 1
            host = random.choice(hosts)
            row = generate_row(current_time, host, i % points_per_host, rows_count)
            writer.writerow(row)
            current_time += timedelta(minutes=interval_minutes)

    print("✅ Data saved: mock_zabbix_data.csv")
    print("⚠️ Injected Anomalies:")
    for ts, host in anomalies:
        print(f"  - [{ts}] on {host}")


# Initialize and generate anomalies for each host
anomalies = []
host_anomalies = {host: get_anomaly_indexes() for host in hosts}

# Run data generation
if __name__ == "__main__":
    generate_data()
