import os
import csv
import pandas as pd
from datetime import datetime
import serial.tools.list_ports

DXL_KAKI_KANAN                      = [15,17,19,21,23,25]
DXL_KAKI_KIRI                       = [16,18,20,22,24,26]

class Aerora:
    @staticmethod
    def map(x , in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    
    @staticmethod
    def getIndexByNotElement(array,element):
        j = 0
        index = []
        for i in array:
            if(i != element):
                index.append(j)
            j+=1
        return index
    
    @staticmethod
    def getNotValue(array,element):
        index = []
        for i in array:
            if(i != element):
                index.append(int(i))
        return index
    
    @staticmethod
    def getNotValue_v2(array,element):
        j=0
        index_xl320 = []
        index_xm430 = []
        for i in array:
            if(i != element):
                if j in DXL_KAKI_KIRI or j in DXL_KAKI_KANAN or j == 13 or j == 14:
                    index_xm430.append(int(i))
                else:
                    index_xl320.append(int(i))
            j+=1
        return index_xl320, index_xm430
    

    @staticmethod
    def bacaFile_v3(FILE_NAME):
        
        file = open(FILE_NAME)
        csvreader = csv.reader(file)
        header = next(csvreader)

        MOTION_TIME_XM430 = []
        MOTION_TIME_XL320 = []
        MOTION_HEAD = []
        MOTION_HAND = []
        MOTION_FEET = []
        MOTION_DXL = []
        MOTION_DXL_XL320 = []
        MOTION_DXL_XM430 = []
        for row in csvreader:
            MOTION_TIME_XL320.append([row[i] for i in range(1, 14)])
            MOTION_TIME_XM430.append([row[i] for i in range(14, 28)])
            MOTION_DXL.append(row[28:])

            MOTION_DXL_XL320.append(row[28:41])
            MOTION_DXL_XM430.append(row[41:54])

            MOTION_HEAD.append(row[28:31])
            MOTION_HAND.append(row[31:43])
            MOTION_FEET.append(row[43:])
        file.close()

        return MOTION_TIME_XM430, MOTION_TIME_XL320, MOTION_HEAD, MOTION_HAND, MOTION_FEET, MOTION_DXL, MOTION_DXL_XL320, MOTION_DXL_XM430
    
    @staticmethod
    def list_available_ports():
        try:
            ports = serial.tools.list_ports.comports()
            available_ports = []
            for port in ports:
                available_ports.append(f"{port.device} - {port.description}")
            return available_ports
        except Exception as e:
            print(f"Error listing ports: {e}")
            return []

    @staticmethod
    def check_port_exists(DEVICENAME):
        try:
            ports = serial.tools.list_ports.comports()
            available_devices = [port.device for port in ports]
            return DEVICENAME in available_devices
        except Exception as e:
            print(f"Error checking port: {e}")
            return False
        
    @staticmethod
    def cek_header_csv(file_path):
        expected_header = []

        expected_header.append("NAME")
        for i in range(13):
            expected_header.append(f"T_XL320#{i}")
        for i in range(13, 27):
            expected_header.append(f"T_XM430#{i}")
        for i in range(27):
            expected_header.append(f"DXL#{i}")

        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                actual_header = next(reader)

                # Cek header dulu
                if actual_header != expected_header:
                    print("Header tidak sesuai")
                    return False
                
                # Baru cek isi (body)
                for line_num, row in enumerate(reader, start=2):
                    if len(row) != len(expected_header):
                        print(f"Baris {line_num} jumlah kolom salah: {len(row)} (harus {len(expected_header)})")
                        return False
                return True

        except Exception as e:
            print("Error:", e)
            return False

    @staticmethod
    def cek_file(path):
        try:
            if not os.path.exists(path):
                raise Exception("File tidak ada")
            if not Aerora.cek_header_csv(path):
                raise Exception("Header atau body pada file salah")
            
            return True, "success"
        except Exception as e:
            return False, e

    @staticmethod    
    def summarize_data(df, metode):
        return {
            "Metode": metode,
            "Jumlah Iterasi": len(df),
            "Rata-rata Waktu Operasi (ms)": df["Waktu_Operasi_ms"].mean(),
            "Waktu Operasi Maksimum (ms)": df["Waktu_Operasi_ms"].max(),
            "Waktu Operasi Minimum (ms)": df["Waktu_Operasi_ms"].min(),
            "Total Error": df["Jumlah_Error"].sum(),
            "Total Recovery": df["Recovery_Count"].sum(),
            "Total Timeout": (df["Timeout"] > 0).sum(),
            "Rata-rata CPU End (%)": df["CPU_Usage_End_%"].mean(),
            "Rata-rata Memory (MB)": df["Memory_Usage_MB"].mean(),
            "Rata-rata Waktu Write (ms)": df["Waktu_Write_ms"].mean(),
            "Rata-rata Waktu Read (ms)": df["Waktu_Read_ms"].mean()
        }

    @staticmethod
    def generate_interpretasi(g, ng):
        lines = []
        lines.append(f"Total data GroupSync: {int(g['Jumlah Iterasi'])}")
        lines.append(f"Total data NonGroupSync: {int(ng['Jumlah Iterasi'])}")
        lines.append("")

        if g["Rata-rata Waktu Operasi (ms)"] < ng["Rata-rata Waktu Operasi (ms)"]:
            lines.append("GroupSync lebih cepat secara rata-rata.")
        else:
            lines.append("NonGroupSync lebih cepat secara rata-rata.")

        if g["Total Error"] > ng["Total Error"]:
            lines.append("NonGroupSync menghasilkan total error lebih sedikit.")
        elif g["Total Error"] < ng["Total Error"]:
            lines.append("GroupSync menghasilkan total error lebih sedikit.")
        else:
            lines.append("Keduanya menghasilkan jumlah error yang sama.")

        if g["Rata-rata CPU End (%)"] > ng["Rata-rata CPU End (%)"]:
            lines.append("GroupSync menggunakan CPU lebih tinggi.")
        else:
            lines.append("NonGroupSync menggunakan CPU lebih tinggi.")

        if g["Total Recovery"] == 0 and ng["Total Recovery"] == 0:
            lines.append("Tidak ada recovery yang terjadi.")
        if g["Total Timeout"] == 0 and ng["Total Timeout"] == 0:
            lines.append("Tidak ada timeout yang terjadi.")

        return "\n".join(lines)

    @staticmethod
    def analisis_global(identitas):
        input_folder = "./data"
        output_folder = "./hasil"
        os.makedirs(output_folder, exist_ok=True)

        group_dfs = []
        nongroup_dfs = []

        for f in os.listdir(input_folder):
            if not f.endswith(".csv"):
                continue
            path = os.path.join(input_folder, f)
            df = pd.read_csv(path)
            if f"groupsync_{identitas}" in f.lower():
                group_dfs.append(df)
            elif f"nongroup_{identitas}" in f.lower():
                nongroup_dfs.append(df)

        if not group_dfs or not nongroup_dfs:
            message = "❌ Tidak ditemukan file GroupSync atau NonGroupSync."
            return False, message

        df_group_all = pd.concat(group_dfs, ignore_index=True)
        df_nongroup_all = pd.concat(nongroup_dfs, ignore_index=True)

        summary_group = Aerora.summarize_data(df_group_all, "GroupSync")
        summary_nongroup = Aerora.summarize_data(df_nongroup_all, "NonGroupSync")

        df_summary = pd.DataFrame([summary_group, summary_nongroup])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_out = os.path.join(output_folder, f"summary_global_{timestamp}.csv")
        txt_out = os.path.join(output_folder, f"summary_global_{timestamp}.txt")

        df_summary.to_csv(csv_out, index=False)
        hasil_group = ''
        hasil_nongroup = ''
        flow = 0
        fllow = 0
        with open(txt_out, "w") as f:
            for _, row in df_summary.iterrows():
                if fllow == 0:
                    hasil_group += f"Metode: {row['Metode']}\n"
                else:
                    hasil_nongroup += f"Metode: {row['Metode']}\n"
                f.write(f"Metode: {row['Metode']}\n")
                for col in df_summary.columns:
                    if col != "Metode":
                        if flow == 1:
                            hasil_group += f"  {col}: {row[col]:.2f}\n"
                        else:
                            hasil_nongroup += f"  {col}: {row[col]:.2f}\n"
                        f.write(f"  {col}: {row[col]:.2f}\n")
                    else:
                        flow += 1
                fllow += 1
                f.write("\n")
            interpretasi = "Interpretasi:\n"
            interpretasi += Aerora.generate_interpretasi(summary_group, summary_nongroup)
            f.write(interpretasi)
        message = []
        message.append(hasil_group)
        message.append(hasil_nongroup)
        message.append(interpretasi)
        return True, message
