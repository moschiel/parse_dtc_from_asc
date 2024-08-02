import re
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk

file_path = 'example_files/VWConstel2024_1.asc'
# file_path = 'example_files/VWConstel2024_2.asc'

# Print control variables
PRINT_DM1_SINGLE_FRAME = False
PRINT_TP_CT = False
PRINT_TP_DT = False
PRINT_J1939TP_FECAp = False
PRINT_TP_DM1_MULTI_FRAME = False
PRINT_INCORRET_ORDER = False
PRINT_DM1_PARSED = False
PRINT_ACTIVE_DTCs = False
PRINT_NEW_ACTIVE_DTCs = False
PRINT_REMOVED_ACTIVE_DTCs = False
PRINT_REMOVED_CANDIDATE_DTCs = False


# List to store active faults
candidate_faults = []
active_faults = []
timeline_faults = []

debounce_fault_inactive = 20 # Remove faults that have not been updated by this amount of time (seconds)
debounce_fault_active_count = 10  # Number of occurrences to consider fault active
debounce_fault_active_time = 10  # Time window in seconds to consider fault active

# Control variables for emulating time
last_time = 0.0 
last_displayed_timestamp = 0.0
end_time = 0

# GUI reference
root = None
tree = None
timestamp_label = None
progress_var = None

# Flags
stop_thread = True
finished_thread = False
close_app = False
app_mode = None

# Dictionary to store descriptions
source_descriptions = {}
spn_descriptions = {}
fmi_descriptions = {}

# Function to load SOURCE descriptions from file
def load_source_descriptions(file_path):
    global source_descriptions
    with open(file_path, 'r') as file:
        for line in file:
            try:
                parts = line.strip().split(';')
                source_descriptions[int(parts[0])] = parts[1]
            except Exception as ex:
                print(f"load_source_descriptions, line: {line}, error: {ex}")
                sys.exit()

# Function to load SPN descriptions from file
def load_spn_descriptions(file_path):
    global spn_descriptions
    with open(file_path, 'r') as file:
        for line in file:
            try:
                parts = line.strip().split(';')
                spn_descriptions[int(parts[0])] = parts[1]
            except Exception as ex:
                print(f"load_spn_descriptions, line: {line}, error: {ex}")
                sys.exit()

# Function to load FMI descriptions from file
def load_fmi_descriptions(file_path):
    global fmi_descriptions
    with open(file_path, 'r') as file:
        for line in file:
            try:
                parts = line.strip().split(';')
                fmi_descriptions[int(parts[0])] = parts[1]
            except Exception as ex:
                print(f"load_fmi_descriptions, line: {line}, error: {ex}")
                sys.exit()

# Function to parse BAM TP:CM message
def parse_tp_cm_message(line):
    parts = line.split()
    timestamp = parts[0]
    message_id = parts[2]
    data_bytes = parts[6:14]

    control_byte = data_bytes[0]

    # Check if it's a BAM message 0x20 (32)
    if control_byte == '20': 
        total_size = int(data_bytes[2] + data_bytes[1], 16)
        num_packets = int(data_bytes[3], 16)
        reserved = data_bytes[4]
        pgn = int(data_bytes[7] + data_bytes[6] + data_bytes[5], 16)
        return timestamp, message_id, total_size, num_packets, pgn
    else:
        sys.exit(f'**** NOT BAM MESSAGE, MSG TYPE IS 0x{control_byte}')
    return None

# Function to parse BAM TP.DT message
def parse_tp_dt_message(line):
    parts = line.split()
    timestamp = parts[0]
    message_id = parts[2]
    data_bytes = parts[6:14]

    packet_number = int(data_bytes[0], 16)
    data = data_bytes[1:8]
    return timestamp, message_id, packet_number, data

# Check if the second byte of the CAN identifier is EC
def is_tp_cm_message_id(message_id):
    message_id = message_id.zfill(8)  # Ensure the identifier has 8 characters
    return message_id[2:4] == 'EC'

# Check if the second byte of the CAN identifier is EB
def is_tp_dt_message_id(message_id):
    message_id = message_id.zfill(8)  # Ensure the identifier has 8 characters
    return message_id[2:4] == 'EB'

# Check if the second and third bytes of the CAN identifier are FECA
def is_dm1_message_id(message_id):
    message_id = message_id.zfill(8)  # Ensure the identifier has 8 characters
    return message_id[2:6] == 'FECA'

# Convert each byte to an 8-bit binary string and join all into one string
def bytes_to_binary_string(byte_list):
    binary_string = ''.join(format(byte, '08b') for byte in byte_list)
    return binary_string

def print_active_faults():
    if PRINT_ACTIVE_DTCs == False or app_mode != 'EMULATE_TIME':
        return
    print(f'Active Faults:')
    global active_faults
    for fault in active_faults: 
        print(f"        SRC: 0x{fault['src']} ({int(fault['src'], 16)}), SPN: 0x{format(fault['spn'], 'X')} ({fault['spn']}), FMI: {fault['fmi']}, MIL: {fault['mil']}, RSL: {fault['rsl']}, AWL: {fault['awl']}, PL: {fault['pl']}")

def fault_to_tupple(fault):
    try:
        src_description = source_descriptions.get(int(fault['src'], 16), "")
        spn_description = spn_descriptions.get(fault['spn'], "")
        fmi_description = fmi_descriptions.get(fault['fmi'], "")
    except Exception as ex:
        print(f"fault_to_tupple, src: {fault['src']}, spn: {fault['spn']}, fmi: {fault['fmi']}, error: {ex}")
        sys.exit()
        return

    return (
            fault['last_seen'],
            fault['status'],
            f"0x{fault['src']} ({int(fault['src'], 16)}) - {src_description}", 
            f"0x{format(fault['spn'], 'X')} ({fault['spn']}) - {spn_description}", 
            f"{fault['fmi']} - {fmi_description}",
            fault['cm'], 
            fault['oc'], 
            fault['mil'], 
            fault['rsl'], 
            fault['awl'], 
            fault['pl']
        )


# Function to update the active faults list
def update_active_faults(src, spn, fmi, cm, oc, mil, rsl, awl, pl, float_timestamp):
    global active_faults
    global tree

    updatedExistingFault = False
    # Update if exist on list already
    for fault in active_faults:
        if fault['src'] == src and fault['spn'] == spn and fault['fmi'] == fmi:
            fault['cm'] = cm
            fault['oc'] = oc
            fault['mil'] = mil
            fault['rsl'] = rsl
            fault['awl'] = awl
            fault['pl'] = pl
            fault['last_seen'] = float_timestamp
            if(fault['status'] == 'candidate'):
                fault['occurrences'] += 1
            updatedExistingFault = True

    # Add new candidate fault to the fault list
    if not updatedExistingFault:
        active_faults.append({
            'src': src,
            'spn': spn,
            'fmi': fmi,
            'cm': cm,
            'oc': oc,
            'mil': mil,
            'rsl': rsl,
            'awl': awl,
            'pl': pl,
            'last_seen': float_timestamp,
            'first_seen': float_timestamp,
            'occurrences': 1,
            'status': 'candidate'
        })
    
    # Verify if 'candidate' fault is elegible to become 'active'
    for fault in active_faults:
        if(fault['status'] == 'candidate'): # is candidate
            if((float_timestamp - fault['first_seen']) <= debounce_fault_active_time): # if debounce active timeout
                if(fault['occurrences'] >= debounce_fault_active_count): #if has the minimum amount of occurrences
                    fault['status'] = 'active' # set as active
                    if app_mode == 'SHOW_TIMELINE':
                        values = fault_to_tupple(fault)
                        tag = 'active'
                        tree.insert('', 'end', values=values, tags=(tag,))
                    if PRINT_NEW_ACTIVE_DTCs:
                        print(f'{float_timestamp} new fault SRC: 0x{src} ({int(src, 16)}), SPN: 0x{format(spn, 'X')} ({spn}), FMI: {fmi}')

    added_new_faults = not updatedExistingFault
    return added_new_faults

# Remove faults that have not been updated for a certain time
# or if they are not 'candidate' anymore
def remove_inactive_faults(float_timestamp):
    # if app_mode != 'EMULATE_TIME':
        # return

    global active_faults
    global debounce_fault_inactive
    current_time = float_timestamp
    new_active_faults = []
    removed = False
    for fault in active_faults:
        if(fault['status'] == 'candidate'): # candidate fault, do not keep on list if it is not a candidate anymore
            if((float_timestamp - fault['first_seen']) <= debounce_fault_active_time):
                new_active_faults.append(fault)
            else:
                if PRINT_REMOVED_CANDIDATE_DTCs: 
                    print(f"{float_timestamp} removed CANDIDATE fault SRC: 0x{fault['src']} ({int(fault['src'], 16)}), SPN: 0x{format(fault['spn'], 'X')} ({fault['spn']}), FMI: {fault['fmi']}")
                removed = True
        else: # active fault, do not keep on list if it is not active anymore
            if current_time - fault['last_seen'] <= debounce_fault_inactive:
                new_active_faults.append(fault)
            else:
                if app_mode == 'SHOW_TIMELINE':
                    aux_fault = fault
                    aux_fault['status'] = 'inactive'
                    values = fault_to_tupple(aux_fault)
                    tag = 'inactive'
                    tree.insert('', 'end', values=values, tags=(tag,))
                if PRINT_REMOVED_ACTIVE_DTCs: 
                    print(f"{float_timestamp} removed fault SRC: 0x{fault['src']} ({int(fault['src'], 16)}), SPN: 0x{format(fault['spn'], 'X')} ({fault['spn']}), FMI: {fault['fmi']}")
                removed = True
    
    active_faults = new_active_faults
    if removed:
        update_active_faults_display()
        print_active_faults()

# Function to parse DM1 message
def parse_dm1_message(timestamp, src, data_bytes):
    mil = (data_bytes[0] >> 6) & 0x03  # byte1, 2bits, Malfunction Indicator Lamp status
    rsl = (data_bytes[0] >> 4) & 0x03  # byte1, 2bits, Red Stop Lamp status
    awl = (data_bytes[0] >> 2) & 0x03  # byte1, 2bits, Amber Warning Lamp status
    pl = data_bytes[0] & 0x03          # byte1, 2bits, Protect Lamp status
    rfu = data_bytes[1]                # byte2, reserved
    if PRINT_DM1_PARSED:
        print(f"DM1 -> Time: {timestamp}, SRC: 0x{src} ({int(src, 16)}), MIL: {mil}, RSL: {rsl}, AWL: {awl}, PL: {pl}")
    
    added_new_faults = False
    # Starting at third byte, iterate 4 bytes each cycle
    j = 1
    for i in range(2, len(data_bytes) - 2, 4):
        spn = (((data_bytes[i + 2] >> 5) & 0x7) << 16) | ((data_bytes[i + 1] << 8) & 0xFF00) | data_bytes[i]
        fmi = data_bytes[i + 2] & 0x1F  # byte5, 5bits, Failure Module Indicator
        cm = (data_bytes[i + 3] >> 7) & 0x01  # byte6, 1bit, Conversion Method
        oc = data_bytes[i + 3] & 0x7F  # byte6, 7bits, Occurrence Counter 
        if PRINT_DM1_PARSED:
            print(f"        DTC[{j}] -> SPN: 0x{format(spn, 'X')} ({spn}), FMI: {fmi}, CM: {cm}, OC: {oc}")
        
        if update_active_faults(src, spn, fmi, cm, oc, mil, rsl, awl, pl, float(timestamp)):
            added_new_faults = True
        j += 1

    update_active_faults_display()
    if added_new_faults:
        print_active_faults()

# Sleep to emulate log execution time
def emulate_waiting_time(float_timestamp):
    if app_mode == 'EMULATE_TIME':
        global last_time
        if last_time != 0:
            time_diff = float_timestamp - last_time
            if time_diff > 0:
                time.sleep(time_diff)
        last_time = float_timestamp

def clear_control_variables():
    global last_time
    global last_displayed_timestamp
    global tree
    global treeview_items
    global timestamp_label
    global progress_var
    global root
    
    last_time = 0
    last_displayed_timestamp = 0
    treeview_items = {}
    timestamp_label.config(text="Time: 0s")
    progress_var.set(0)
    for item in tree.get_children(): #delete all rows from GUI
        tree.delete(item)
    root.update_idletasks()

def update_screen_time(float_timestamp):
    if app_mode != 'EMULATE_TIME':
        return
    global last_displayed_timestamp
    if float_timestamp - last_displayed_timestamp >= 1:
        last_displayed_timestamp = float_timestamp
        global timestamp_label
        global end_time
        global progress_var
        global root
        timestamp_label.config(text=f"Time: {int(float_timestamp)}s")
        percent = (float_timestamp / end_time) * 100
        progress_var.set(percent)
        root.update_idletasks()
        if(percent >= 100):
            global stop_thread
            stop_thread = True

# Function to get the end timestamp from the log file
def get_end_time(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in reversed(lines):
            if 'Rx' in line:
                parts = line.split()
                timestamp = float(parts[0])
                return timestamp
    return 0

# Main function to read log file and print DTCs from individual frames or from BAM frames
def read_log_and_print_dtc(file_path):
    #Reset all variables
    clear_control_variables()
    current_bams = []  # List to store current BAM messages
    started_measurement = False

    with open(file_path, 'r') as file:
        for line in file:
            if stop_thread:
                break

            if started_measurement == False:
                if 'Start of measurement' in line:
                    started_measurement = True
                else:
                    continue

            parts = line.split()
            timestamp = parts[0]
            
            try:
                float_timestamp = float(timestamp)
            except Exception as ex:
                print(f"Error reading timestamp: {ex}")
                continue

            emulate_waiting_time(float_timestamp)
            update_screen_time(float_timestamp)
            
            if 'Rx' in line:
                if 'J1939TP FECAp' in line:  
                    if PRINT_J1939TP_FECAp:
                        print(line.strip())

                message_id = parts[2]  # CAN ID
                src = message_id.zfill(8)[6:8]  # source, last byte of CAN ID

                if is_dm1_message_id(message_id):
                    data_bytes = [int(b, 16) for b in parts[6:14]]
                    spn = (((data_bytes[4] >> 5) & 0x7) << 16) | ((data_bytes[3] << 8) & 0xFF00) | data_bytes[2]
                    if spn != 0:
                        if PRINT_DM1_SINGLE_FRAME:
                            print(line.strip())
                        parse_dm1_message(timestamp, src, data_bytes)
                elif is_tp_cm_message_id(message_id):  # Identify BAM message
                    result = parse_tp_cm_message(line)
                    if result:
                        timestamp, message_id, total_size, num_packets, pgn = result

                        if pgn != 65226:  # If it is not DM1 (0xFECA), ignore it
                            continue

                        # TP.CT version of the TP.CM message
                        message_id_tp_ct = message_id.replace('EC', 'EB', 1)

                        for bam in current_bams:
                            if bam['message_id'] == message_id:
                                current_bams.remove(bam)

                        current_bams.append({
                            'timestamp': timestamp,
                            'message_id': message_id,
                            'message_id_tp_ct': message_id_tp_ct,
                            'total_size': total_size,
                            'num_packets': num_packets,
                            'pgn': pgn,
                            'packets': []
                        })
                        if PRINT_TP_CT:
                            print(f"TP.CT -> Time: {timestamp}, ID: {message_id}, Size: {total_size} bytes, Number of Packets: {num_packets}, PGN: {pgn:#X}")
                elif is_tp_dt_message_id(message_id):  # Identify TP.DT message
                    result = parse_tp_dt_message(line)
                    if result:
                        timestamp, message_id, packet_number, data = result
                        if PRINT_TP_DT:
                            print(f"TP.DT ->  Time: {timestamp}, ID: {message_id}, Packet Number: {packet_number}, Data: {' '.join(data)}")
                        
                        for bam in current_bams:
                            if bam['message_id_tp_ct'] == message_id:
                                if packet_number != (len(bam['packets']) + 1):
                                    if PRINT_INCORRET_ORDER:
                                        print('Packet Order is Incorrect')
                                    current_bams.remove(bam)
                                    break

                                bam['packets'].append((packet_number, data))
                                if len(bam['packets']) == bam['num_packets']:
                                    bam['packets'].sort()
                                    combined_data = []
                                    for packet in bam['packets']:
                                        combined_data.extend(packet[1])
                                    combined_data = combined_data[:bam['total_size']]

                                    if PRINT_TP_DM1_MULTI_FRAME:
                                        print(f"TP -> Time: {bam['timestamp']}, ID: {bam['message_id']}, Size: {bam['total_size']}, Data: {' '.join(combined_data)}")
                                    
                                    data_bytes = [int(b, 16) for b in combined_data]
                                    parse_dm1_message(timestamp, src, data_bytes)
                                    
                                    current_bams.remove(bam)
                                    break

                remove_inactive_faults(float_timestamp)

# Dictionary to store references to treeview items
treeview_items = {}
def update_active_faults_display():
    if app_mode != 'EMULATE_TIME':
        return

    global treeview_items
    global tree

    current_fault_keys = {(fault['src'], fault['spn'], fault['fmi']) for fault in active_faults}

    for fault in active_faults:
        key = (fault['src'], fault['spn'], fault['fmi'])
        values = fault_to_tupple(fault)
        tag = fault['status']
        
        if key in treeview_items:
            tree.item(treeview_items[key], values=values)
            tree.item(treeview_items[key], tags=(tag,))
        else:
            item_id = tree.insert('', 'end', values=values, tags=(tag,))
            treeview_items[key] = item_id

    for key in list(treeview_items.keys()):
        if key not in current_fault_keys:
            values = tree.item(treeview_items[key], 'values')
            # Atualizar a segunda coluna (índice 1 / status) para um novo valor 'inactive'
            new_values = (values[0], 'inactive', *values[2:])
            tree.item(treeview_items[key], values=new_values)
            tree.item(treeview_items[key], tags=('inactive',))


def init_app():
    # Load descriptions
    load_source_descriptions('database/sources.txt')
    load_spn_descriptions('database/spn.txt')
    load_fmi_descriptions('database/fmi.txt')

    global root
    root = tk.Tk()
    root.title("Active Faults")
    root.geometry("900x500")

    columns = ('Last Seen', 'Status', 'SRC', 'SPN', 'FMI', 'CM', 'OC', 'MIL', 'RSL', 'AWL', 'PL')
    
    global tree
    tree = ttk.Treeview(root, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=80)
    tree.pack(fill=tk.BOTH, expand=True)
    
    tree.tag_configure('active', background='lightgreen')
    tree.tag_configure('inactive', background='lightgrey')
    tree.tag_configure('candidate', background='white')

    def read_log_thread(file_path):
        global stop_thread
        global finished_thread
        global close_app
        while True:
            if not stop_thread and not finished_thread:
                read_log_and_print_dtc(file_path)
                finished_thread = True
            elif close_app:
                return


    read_log_thread = threading.Thread(target=read_log_thread, args=(file_path,))

    def on_start_emulation():
        global stop_thread
        global app_mode
        global finished_thread
        if not stop_thread:
            return
        if app_mode == 'EMULATE_TIME':
            return
        app_mode = 'EMULATE_TIME'
        stop_thread = False
        finished_thread = False
        try:
            read_log_thread.start()
        except Exception as ex:
            print(f"fail to start read_log_thread: {ex}")

    def on_show_timeline():
        global stop_thread
        global app_mode
        global finished_thread
        if not stop_thread:
            return
        if app_mode == 'SHOW_TIMELINE':
            return
        app_mode = 'SHOW_TIMELINE'
        stop_thread = False
        finished_thread = False
        try:
            read_log_thread.start()
        except Exception as ex:
            print(f"fail to start read_log_thread: {ex}")

    def on_stop():
        global stop_thread
        global app_mode
        stop_thread = True
        finished_thread = False
        app_mode = None

    # Frame to hold the buttons horizontally
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)

    start_time_emulation_button = tk.Button(button_frame, text="Start Time Emulation", command=on_start_emulation,)
    start_time_emulation_button.pack(side=tk.LEFT, padx=5)

    display_history_timeline_button = tk.Button(button_frame, text="Show Complete Timeline", command=on_show_timeline)
    display_history_timeline_button.pack(side=tk.LEFT, padx=5)

    stop_button = tk.Button(button_frame, text="Stop", command=on_stop)
    stop_button.pack(side=tk.LEFT, padx=5)

    # global timestamp_label
    # timestamp_label = tk.Label(root, text="Time: 0s")
    # timestamp_label.pack()

    # Frame to hold the inputs horizontally
    input_frame = tk.Frame(root)
    input_frame.pack(pady=20)

    count_active_frame = tk.Frame(input_frame)
    count_active_frame.pack(side=tk.LEFT, padx=5)
    debounce_active_count_label = tk.Label(count_active_frame, text="Debounce Fault Active Count:")
    debounce_active_count_label.pack()
    debounce_active_count_entry = tk.Entry(count_active_frame)
    debounce_active_count_entry.pack()
    debounce_active_count_entry.insert(0, str(debounce_fault_active_count))

    debounce_active_frame = tk.Frame(input_frame)
    debounce_active_frame.pack(side=tk.LEFT, padx=5)
    debounce_active_time_label = tk.Label(debounce_active_frame, text="Debounce Fault Active Time (seconds):")
    debounce_active_time_label.pack()
    debounce_active_time_entry = tk.Entry(debounce_active_frame)
    debounce_active_time_entry.pack()
    debounce_active_time_entry.insert(0, str(debounce_fault_active_time))

    inactive_frame = tk.Frame(input_frame)
    inactive_frame.pack(side=tk.LEFT, padx=5)
    debounce_inactive_label = tk.Label(inactive_frame, text="Debounce Fault Inactive Time (seconds):")
    debounce_inactive_label.pack()
    debounce_inactive_entry = tk.Entry(inactive_frame)
    debounce_inactive_entry.pack()
    debounce_inactive_entry.insert(0, str(debounce_fault_inactive))

    def update_configs():
        global debounce_fault_inactive, debounce_fault_active_count, debounce_fault_active_time
        try:
            debounce_fault_inactive = float(debounce_inactive_entry.get())
            debounce_fault_active_count = int(debounce_active_count_entry.get())
            debounce_fault_active_time = float(debounce_active_time_entry.get())
        except ValueError:
            pass

    configs_button = tk.Button(input_frame, text="Update Configs", command=update_configs)
    configs_button.pack(side=tk.LEFT, padx=5)

    # frame to hold timestamp and progressbar
    progress_frame = tk.Frame(root)
    progress_frame.pack(pady=20, fill=tk.X, expand=True)
    global timestamp_label
    timestamp_label = tk.Label(progress_frame, text="Time: 0s")
    timestamp_label.pack(side=tk.LEFT, padx=5)
    global progress_var
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
    progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    global end_time
    end_time = get_end_time(file_path)

    def on_closing():
        global stop_thread
        stop_thread = True
        global close_app
        close_app = True
        root.quit()


    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

init_app()
