# -*- coding: utf-8 -*-
import azure.functions as func
import pandas as pd
import xml.etree.ElementTree as ET
import datetime as dt
import numpy as np
from azure.storage.blob import BlobServiceClient
import io
import logging
import os
import json
from io import BytesIO
import unicodedata
import re
from collections import defaultdict
import math
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum 
from azure.storage.filedatalake import DataLakeServiceClient

app = func.FunctionApp()

@app.function_name(name="csv2xml")
@app.route(route="csv2xml", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def csv2xml_function(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to convert CSV files to XML
    Keeps original csv2xml.py logic with minimal changes
    """
    logging.info('Python HTTP trigger function processed a request.')
    
    try:
        # Get date parameter (default to today if not provided)
        date_param = req.params.get('date')
        if not date_param:
            t_delta = dt.timedelta(hours=9)
            JST = dt.timezone(t_delta, 'JST')
            now = dt.datetime.now(JST)
            date_param = format(now, '%Y%m%d')
        
        # Process CSV to XML conversion
        result = csv2xml(date_param)
        
        return func.HttpResponse(
            f"CSV to XML conversion completed for date: {date_param}. {result}",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error in csv2xml_function: {str(e)}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )

def csv2xml(today):
    """
    Main conversion logic - identical to original csv2xml.py
    Only file I/O changed to use blob storage
    """
    # 現在日時の取得
    t_delta = dt.timedelta(hours=9)
    JST = dt.timezone(t_delta, 'JST')
    now = dt.datetime.now(JST)
    time = format(now, '%H%M%S')  # 現在時刻 hhmmss

    # Get blob storage settings from environment variables (for Azure) or use defaults 
    connection_string = os.environ.get(
        'AZURE_STORAGE_CONNECTION_STRING',
        "DefaultEndpointsProtocol=https;AccountName=dwhdeast02strg001dev;AccountKey=maM+BH0McLmG8xcEUe23CrkS95tkaj5gcRAbfOUZ7rDQQbsvSiJPVLA3Alv2tlyJAlUnx0kATgjJAThrKYNusw==;EndpointSuffix=core.windows.net"
    )
    container_name = os.environ.get('AZURE_STORAGE_CONTAINER', 'external')
    base_path = os.environ.get('AZURE_STORAGE_BASE_PATH', 'HC連携/テスト/dynam/send')
    
    # Initialize blob service client
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    
    # フォルダパス取得 (blob prefix)
    folder_path = f"{base_path}/{today}"

    # 各CSVファイルパス取得
    file_list1 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('TEMPO_MODE.csv'):
            file_list1.append(blob.name)

    file_list2 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('TEMPO_SYSTEM_MODE.csv'):
            file_list2.append(blob.name)

    file_list3 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('BLOCK_REPORT.csv'):
            file_list3.append(blob.name)

    file_list4 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('TEMPO_REPORT.csv'):
            file_list4.append(blob.name)

    file_list5 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('S_RATE_TOTAL.csv'):
            file_list5.append(blob.name)

    file_list6 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('YUUGI_FILE.csv'):
            file_list6.append(blob.name)

    file_list7 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('CURRENT_BLOCK.csv'):
            file_list7.append(blob.name)

    file_list8 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('CURRENT_KISYU.csv'):
            file_list8.append(blob.name)

    file_list9 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('CURRENT_COUNT.csv'):
            file_list9.append(blob.name)

    file_list10 = []
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    for blob in blobs:
        if blob.name.endswith('NIPPOU_FILE.csv'):
            file_list10.append(blob.name)

    # XMLファイルパスとXMLファイル名を作成
    output_file_path_list = []
    for path in file_list2:
        # Read CSV from blob to check flags
        blob_data = read_csv_from_blob(container_client, path)
        
        # Find columns containing INDB and OUTDB
        indb_col = None
        outdb_col = None
        for col in blob_data.columns:
            if 'INDB' in str(col):
                indb_col = col
            if 'OUTDB' in str(col):
                outdb_col = col
        
        if indb_col and outdb_col:
            flag = blob_data[[indb_col, outdb_col]].values[0].tolist()
        else:
            logging.warning(f"INDB/OUTDB columns not found in {path}")
            flag = ['0', '0']
        
        # Parse path to extract store info
        # Find the parts that look like date (8 digits) and store (format: XXXXX_YYYYY)
        path_parts = [p for p in path.split('/') if p]  # Remove empty parts
        
        store_folder = None
        date_folder = None
        for i, part in enumerate(path_parts):
            if len(part) == 8 and part.isdigit():  # Found date folder
                date_folder = part
                if i + 1 < len(path_parts) and '_' in path_parts[i + 1]:
                    store_folder = path_parts[i + 1]
                break
        
        if store_folder and '_' in store_folder:
            store_number = store_folder.split('_')[-1]
        else:
            store_number = '00000'
        
        if not store_folder:
            store_folder = '00000_00000'
        
        # Reconstruct proper output path using base_path
        if flag[0] == '1' and flag[1] == '1':
            filename = f"JISSEKI_{store_number}_{today[:4]}-{today[4:6]}-{today[6:8]}_LAST.dynam"
        else:
            filename = f"JISSEKI_{store_number}_{today[:4]}-{today[4:6]}-{today[6:8]}_{time}.dynam"
        
        # Build proper path: base_path/date/store_folder/xml/filename
        output_file_path = f"{base_path}/{today}/{store_folder}/xml/{filename}"
        output_file_path_list.append(output_file_path)

    # CSVファイルパスとXMLファイルパスを2次元配列にまとめる
    file_list = [file_list1, file_list2, file_list3, file_list4, file_list5, 
                 file_list6, file_list7, file_list8, file_list9, file_list10, 
                 output_file_path_list]

    # 2次元配列を転置して縦並べ毎のCSVファイルパスとXMLファイルパスにする
    file = np.array(file_list).T

    # 各CSVファイル読み込みとXMLファイル出力設定してループ
    processed_count = 0
    for df in file:
        df1 = read_csv_from_blob(container_client, df[0])
        df2 = read_csv_from_blob(container_client, df[1])
        df3 = read_csv_from_blob(container_client, df[2])
        df4 = read_csv_from_blob(container_client, df[3])
        df5 = read_csv_from_blob(container_client, df[4])
        df6 = read_csv_from_blob(container_client, df[5])
        df7 = read_csv_from_blob(container_client, df[6])
        df8 = read_csv_from_blob(container_client, df[7])
        df9 = read_csv_from_blob(container_client, df[8])
        df10 = read_csv_from_blob(container_client, df[9])
        output_file = df[10]

        # ルート要素作成
        root = ET.Element('実行集計データ')

        child = ET.SubElement(root, 'データフォーマット区分')
        ET.SubElement(child, 'XMLデータフォーマットバージョン番号').text = str('1.0')
    
        for index, row in df1.iterrows():
            child = ET.SubElement(root, '台場情報')
            for col_name in df1.columns:
                col_value = row[col_name]
                ET.SubElement(child, col_name).text = str(col_value)

        for index, row in df2.iterrows():
            child = ET.SubElement(root, '台場システムモード')
            for col_name in df2.columns:
                col_value = row[col_name]
                ET.SubElement(child, col_name).text = str(col_value)

        child = ET.SubElement(root, 'ブロック明細')
        for index, row in df3.iterrows():
            child2 = ET.SubElement(child, "ROW", num=str(int(index)+1))
            for col_name in df3.columns:
                col_value = row[col_name]
                ET.SubElement(child2, col_name).text = str(col_value)

        child = ET.SubElement(root, '台場統計')
        for index, row in df4.iterrows():
            child2 = ET.SubElement(child, "ROW", num=str(int(index)+1))
            for col_name in df4.columns:
                col_value = row[col_name]
                ET.SubElement(child2, col_name).text = str(col_value)

        child = ET.SubElement(root, '遊技機データ')
        child = ET.SubElement(root, '実行集計データ')

        child = ET.SubElement(root, '実行レート別集計データ')
        for index, row in df5.iterrows():
            child2 = ET.SubElement(child, "ROW", num=str(int(index)+1))
            for col_name in df5.columns:
                col_value = row[col_name]
                ET.SubElement(child2, col_name).text = str(col_value)

        child = ET.SubElement(root, '試算結果データ')
        for index, row in df6.iterrows():
            child2 = ET.SubElement(child, "ROW", num=str(int(index)+1))
            for col_name in df6.columns:
                col_value = row[col_name]
                ET.SubElement(child2, col_name).text = str(col_value)

        child = ET.SubElement(root, 'カレントブロック情報')
        for index, row in df7.iterrows():
            child2 = ET.SubElement(child, "ROW", num=str(int(index)+1))
            for col_name in df7.columns:
                col_value = row[col_name]
                ET.SubElement(child2, col_name).text = str(col_value)

        child = ET.SubElement(root, 'カレント機種情報')
        for index, row in df8.iterrows():
            child2 = ET.SubElement(child, "ROW", num=str(int(index)+1))
            for col_name in df8.columns:
                col_value = row[col_name]
                ET.SubElement(child2, col_name).text = str(col_value)

        child = ET.SubElement(root, 'カレントコーナー情報')
        child = ET.SubElement(root, 'カレント機種グループ情報')

        child = ET.SubElement(root, 'カレント売上管理情報')
        for index, row in df9.iterrows():
            child2 = ET.SubElement(child, "ROW", num=str(int(index)+1))
            for col_name in df9.columns:
                col_value = row[col_name]
                ET.SubElement(child2, col_name).text = str(col_value)

        child = ET.SubElement(root, '日報明細')

        child = ET.SubElement(root, '売上別日報明細')
        for index, row in df10.iterrows():
            child2 = ET.SubElement(child, "ROW", num=str(int(index)+1))
            for col_name in df10.columns[0:1]:
                col_value = row[col_name]
                ET.SubElement(child2, col_name).text = str(col_value)
                child3 = ET.SubElement(child2, 'プレ機種時間情報')
                for col_name in df10.columns[1:5]:
                    col_value = row[col_name]
                    ET.SubElement(child3, col_name).text = str(col_value)
                child4 = ET.SubElement(child2, 'POS時間情報')
                for col_name in df10.columns[5:17]:
                    col_value = row[col_name]
                    ET.SubElement(child4, col_name).text = str(col_value)
                child5 = ET.SubElement(child2, 'POS時間個別情報')
                for col_name in df10.columns[17:34]:
                    col_value = row[col_name]
                    ET.SubElement(child5, col_name).text = str(col_value)
                child6 = ET.SubElement(child2, '会員個別情報')
                for col_name in df10.columns[34:40]:
                    col_value = row[col_name]
                    ET.SubElement(child6, col_name).text = str(col_value)
                child7 = ET.SubElement(child2, '売上別遊技時間内訳')
                for col_name in df10.columns[40:51]:
                    col_value = row[col_name]
                    ET.SubElement(child7, col_name).text = str(col_value)
                child8 = ET.SubElement(child2, '売上別景品情報')
                for col_name in df10.columns[51:55]:
                    col_value = row[col_name]
                    ET.SubElement(child8, col_name).text = str(col_value)
                child9 = ET.SubElement(child2, '売上別遊技会員割合')
                for col_name in df10.columns[55:63]:
                    col_value = row[col_name]
                    ET.SubElement(child9, col_name).text = str(col_value)

        # XMLを出力 (to blob storage)
        ET.indent(root, space='  ')
        xml_bytes = ET.tostring(root, encoding="shift_jis", xml_declaration=True)
        
        # Upload to blob
        blob_client = container_client.get_blob_client(output_file)
        blob_client.upload_blob(xml_bytes, overwrite=True)
        logging.info(f"XML uploaded to: {output_file}")
        
        processed_count += 1
    
    return f"Processed {processed_count} file groups"

def load_csv_schemas():
    try:
        schema_path = os.path.join(os.path.dirname(__file__), 'csv_schemas.json')
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load csv_schemas.json: {str(e)}")
        return {"ZA": [], "ZI": [], "ZK": []}

CSV_SCHEMAS = load_csv_schemas()

def read_csv_from_blob(container_client, blob_path):
    blob_client = container_client.get_blob_client(blob_path)
    blob_data = blob_client.download_blob().readall()
    
    for encoding in ['utf-8', 'cp932', 'shift_jis']:
        try:
            csv_string = blob_data.decode(encoding)
            df = pd.read_csv(io.StringIO(csv_string), dtype=object)
            return df
        except (UnicodeDecodeError, Exception):
            continue
    
    raise ValueError(f"Could not decode {blob_path} with any supported encoding")

@app.route(route="phase1/sd_hc_data_convert", methods=["POST"])
def phase1_sd_hc_data_convert(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        container_name = req_body.get("container_name", "external")
        input_file_xlsx = req_body.get("input_file_xlsx")
        input_sheet_name = req_body.get("input_sheet_name")
        input_folder_path = req_body.get("input_folder_path")
        output_folder_path_today = req_body.get("output_folder_path_today")
        output_folder_path_past = req_body.get("output_folder_path_past")
        input_day = req_body.get("input_day")

        if not input_file_xlsx or not input_folder_path or not output_folder_path_today or not output_folder_path_past:
            return func.HttpResponse(
                json.dumps({"error": "input_file_xlsx, input_folder_path, output_folder_path_today, and output_folder_path_past are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)

        blob_client_xlsx = blob_service.get_blob_client(container=container_name, blob=input_file_xlsx)
        xlsx_data = blob_client_xlsx.download_blob().readall()
        df_xlsx = pd.read_excel(
            BytesIO(xlsx_data),
            sheet_name=input_sheet_name,
            header=None,
            dtype=str
        )

        if df_xlsx.empty:
            return func.HttpResponse(
                json.dumps({"error": "XLSX sheet is empty"}),
                status_code=400,
                mimetype="application/json"
            )
        
        xlsx_patterns = set(
            df_xlsx.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda x: x != ""]
        )
        
        container_client = blob_service.get_container_client(container=container_name)
        
        folder_prefix = input_folder_path.strip("/")
        if folder_prefix and not folder_prefix.endswith("/"):
            folder_prefix += "/"
        
        blobs = container_client.list_blobs(name_starts_with=folder_prefix)
        
        folders = set()
        for blob in blobs:
            blob_path = blob.name[len(folder_prefix):]
            if "/" in blob_path:
                folder_name = blob_path.split("/")[0]
                folders.add(folder_name)
        
        filtered_folders = [f for f in folders if f in xlsx_patterns]
        filtered_folders.sort()
        
        folder_files_mapping = {}
        operation_logs = [] 
        
        if input_day:
            file_types = ["ZA.csv", "ZI.csv", "ZK.csv"]
            
            for folder in filtered_folders:
                folder_path = f"{folder_prefix}{folder}/"
                found_files = []
                
                blobs_in_folder = container_client.list_blobs(name_starts_with=folder_path)
                
                for blob in blobs_in_folder:
                    blob_name = blob.name.split("/")[-1]
                    if (len(blob_name) >= 15 and 
                        blob_name.startswith("01") and 
                        blob_name[2:10].isdigit() and 
                        any(blob_name.endswith(ft) for ft in file_types)):
                        found_files.append(blob_name)
                
                if found_files:
                    folder_files_mapping[folder] = {
                        "files": sorted(found_files),
                        "validated_files": [],
                        "processed_files": []
                    }
                    
                    try:
                        corp, store = folder.split("_", 1)
                    except ValueError:
                        error_msg = f"✗ Invalid folder format (expected corp_store): {folder}"
                        logging.error(error_msg)
                        operation_logs.append(error_msg)
                        continue
                    
                    for file_name in found_files:
                        file_path = f"{folder_path}{file_name}"
                        try:
                            df_csv = read_csv_from_blob(container_client, file_path)
                            
                            if '年月日' in df_csv.columns:
                                csv_day = df_csv['年月日'].iloc[0] if len(df_csv) > 0 else None
                                csv_day_str = str(csv_day).strip() if csv_day is not None else ""
                                
                                file_type = file_name[-6:-4] + "_SD"
                                name = file_name[-6:-4]

                                schema_columns = CSV_SCHEMAS.get(file_type, [])

                                if schema_columns:
                                    df_output = pd.DataFrame()
                                    input_cols = list(df_csv.columns)
                                    
                                    for idx, schema_col in enumerate(schema_columns):
                                        if schema_col in df_csv.columns:
                                            df_output[schema_col] = df_csv[schema_col]
                                        elif idx < len(input_cols):
                                            df_output[schema_col] = df_csv[input_cols[idx]]
                                        else:
                                            df_output[schema_col] = ''
                                    
                                    df_csv = df_output
                                
                                df_csv.insert(0, '会社コード', corp)
                                df_csv.insert(1, '店舗コード', store)
                                
                                if csv_day_str == input_day:
                                    output_folder = output_folder_path_today
                                    match_status = True
                                else:
                                    output_folder = output_folder_path_past
                                    match_status = False
                                
                                output_filename = f"{corp}{store}{csv_day_str}{name}_2.csv"
                                output_folder_structured = f"{output_folder.strip('/')}/{corp}{store}{csv_day_str}/"
                                output_file_path = f"{output_folder_structured}{output_filename}"
                                
                                try:
                                    csv_string = df_csv.to_csv(index=False)
                                    try:
                                        csv_bytes = csv_string.encode('shift_jis')
                                    except UnicodeEncodeError:
                                        csv_bytes = csv_string.encode('cp932', errors='replace')
                                    
                                    blob_client_out = container_client.get_blob_client(output_file_path)
                                    blob_client_out.upload_blob(csv_bytes, overwrite=True)
                                    
                                    folder_files_mapping[folder]["validated_files"].append({
                                        "file_name": file_name,
                                        "date_match": match_status,
                                        "csv_day": csv_day_str
                                    })
                                    
                                    folder_files_mapping[folder]["processed_files"].append({
                                        "original_file": file_name,
                                        "output_file": output_filename,
                                        "output_path": output_file_path,
                                        "output_folder": "today" if match_status else "past"
                                    })
                                    
                                    if match_status:
                                        log_msg = f"✓ Folder: {folder}, File: {file_name}, Day: {csv_day_str} (matches {input_day}) → saved to output_folder_today"
                                        logging.info(log_msg)
                                        operation_logs.append(log_msg)
                                    else:
                                        log_msg = f"✗ Folder: {folder}, File: {file_name}, Day: {csv_day_str} (expected {input_day}) → saved to output_folder_past"
                                        logging.info(log_msg)
                                        operation_logs.append(log_msg)
                                        
                                except Exception as write_error:
                                    folder_files_mapping[folder]["validated_files"].append({
                                        "file_name": file_name,
                                        "error": f"Failed to write output: {str(write_error)}"
                                    })
                                    error_msg = f"✗ Error writing file {file_name} in {folder}: {str(write_error)}"
                                    logging.error(error_msg)
                                    operation_logs.append(error_msg)
                            else:
                                error_msg = f"✗ Folder: {folder}, File: {file_name} - 年月日 column not found"
                                logging.warning(error_msg)
                                operation_logs.append(error_msg)
                                folder_files_mapping[folder]["validated_files"].append({
                                    "file_name": file_name,
                                    "date_match": False,
                                    "error": "年月日 column not found"
                                })
                        except Exception as e:
                            error_msg = f"✗ Error reading file {file_name} in {folder}: {str(e)}"
                            logging.error(error_msg)
                            operation_logs.append(error_msg)
                            folder_files_mapping[folder]["validated_files"].append({
                                "file_name": file_name,
                                "error": str(e)
                            })
        
        result = {
            "status": "success",
            "input_file": input_file_xlsx,
            "input_folder": input_folder_path,
            "output_folder_today": output_folder_path_today,
            "output_folder_past": output_folder_path_past,
            "input_day": input_day,
            "xlsx_data": df_xlsx.to_dict(orient="records"),
            "total_patterns_from_xlsx": len(xlsx_patterns),
            "xlsx_patterns": list(sorted(xlsx_patterns)),
            "all_folders_found": list(sorted(folders)),
            "total_folders_found": len(folders),
            "filtered_folders": filtered_folders,
            "total_filtered_folders": len(filtered_folders),
            "folder_files_mapping": folder_files_mapping,
            "operation_logs": operation_logs,
            "message": f"Found {len(filtered_folders)} matching folders from {len(xlsx_patterns)} XLSX patterns out of {len(folders)} total folders"
        }

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in phase1_SD_hc_data_convert: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="phase1/ma_hc_data_convert", methods=["POST"])
def phase1_ma_hc_data_convert(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        container_name = req_body.get("container_name", "external")
        input_file_xlsx = req_body.get("input_file_xlsx")
        input_sheet_name = req_body.get("input_sheet_name")
        input_folder_path = req_body.get("input_folder_path")
        output_folder_path_today = req_body.get("output_folder_path_today")
        output_folder_path_past = req_body.get("output_folder_path_past")
        input_day = req_body.get("input_day")

        if not input_file_xlsx or not input_folder_path or not output_folder_path_today or not output_folder_path_past:
            return func.HttpResponse(
                json.dumps({"error": "input_file_xlsx, input_folder_path, output_folder_path_today, and output_folder_path_past are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)

        blob_client_xlsx = blob_service.get_blob_client(container=container_name, blob=input_file_xlsx)
        xlsx_data = blob_client_xlsx.download_blob().readall()
        df_xlsx = pd.read_excel(
            BytesIO(xlsx_data),
            sheet_name=input_sheet_name,
            header=None,
            dtype=str
        )

        if df_xlsx.empty:
            return func.HttpResponse(
                json.dumps({"error": "XLSX sheet is empty"}),
                status_code=400,
                mimetype="application/json"
            )
        
        xlsx_patterns = set(
            df_xlsx.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda x: x != ""]
        )
        
        container_client = blob_service.get_container_client(container=container_name)
        
        folder_prefix = input_folder_path.strip("/")
        if folder_prefix and not folder_prefix.endswith("/"):
            folder_prefix += "/"
        
        blobs = container_client.list_blobs(name_starts_with=folder_prefix)
        
        folders = set()
        for blob in blobs:
            blob_path = blob.name[len(folder_prefix):]
            if "/" in blob_path:
                folder_name = blob_path.split("/")[0]
                folders.add(folder_name)
        
        filtered_folders = [f for f in folders if f in xlsx_patterns]
        filtered_folders.sort()
        
        folder_files_mapping = {}
        operation_logs = [] 
        
        if input_day:
            file_types = ["ZA.csv", "ZI.csv", "ZK.csv"]
            
            for folder in filtered_folders:
                folder_path = f"{folder_prefix}{folder}/"
                found_files = []
                
                blobs_in_folder = container_client.list_blobs(name_starts_with=folder_path)
                
                for blob in blobs_in_folder:
                    blob_name = blob.name.split("/")[-1]
                    if (len(blob_name) >= 15 and 
                        blob_name.startswith("01") and 
                        blob_name[2:10].isdigit() and 
                        any(blob_name.endswith(ft) for ft in file_types)):
                        found_files.append(blob_name)
                
                if found_files:
                    folder_files_mapping[folder] = {
                        "files": sorted(found_files),
                        "validated_files": [],
                        "processed_files": []
                    }
                    
                    try:
                        corp, store = folder.split("_", 1)
                    except ValueError:
                        error_msg = f"✗ Invalid folder format (expected corp_store): {folder}"
                        logging.error(error_msg)
                        operation_logs.append(error_msg)
                        continue
                    
                    for file_name in found_files:
                        file_path = f"{folder_path}{file_name}"
                        try:
                            # df_csv = read_csv_from_blob(container_client, file_path)
                            blob_client = container_client.get_blob_client(file_path)
                            blob_data = blob_client.download_blob().readall()

                            df_csv = None
                            for encoding in ['utf-8', 'cp932', 'shift_jis']:
                                try:
                                    csv_string = blob_data.decode(encoding)
                                    df_csv = pd.read_csv(
                                        io.StringIO(csv_string),
                                        header=None,    
                                        dtype=object
                                    )
                                    break
                                except UnicodeDecodeError:
                                    continue
                            name = file_name[-6:-4]
                            file_type = name + "_MA"
                            schema_columns = CSV_SCHEMAS.get(file_type, [])

                            if schema_columns and df_csv.shape[1] == len(schema_columns):
                                df_csv.columns = schema_columns
                            else:
                                raise ValueError(
                                    f"Column count mismatch: csv={df_csv.shape[1]}, schema={len(schema_columns)} ({file_type})"
                                )
                            
                            if '年月日' in df_csv.columns:
                                csv_day = df_csv['年月日'].iloc[0] if len(df_csv) > 0 else None
                                csv_day_str = str(csv_day).strip() if csv_day is not None else ""
                                
                                file_type = file_name[-6:-4] + "_MA"
                                name = file_name[-6:-4]

                                schema_columns = CSV_SCHEMAS.get(file_type, [])
                                
                                if schema_columns:
                                    df_output = pd.DataFrame()

                                    for col in schema_columns:
                                        if col in df_csv.columns:
                                            df_output[col] = df_csv[col]
                                        else:
                                            df_output[col] = ''

                                    df_csv = df_output
                                
                                df_csv.insert(0, '会社コード', corp)
                                df_csv.insert(1, '店舗コード', store)
                                
                                if csv_day_str == input_day:
                                    output_folder = output_folder_path_today
                                    match_status = True
                                else:
                                    output_folder = output_folder_path_past
                                    match_status = False
                                
                                output_filename = f"{corp}{store}{csv_day_str}{name}_2.csv"
                                output_folder_structured = f"{output_folder.strip('/')}/{corp}{store}{csv_day_str}/"
                                output_file_path = f"{output_folder_structured}{output_filename}"
                                
                                try:
                                    csv_string = df_csv.to_csv(index=False)
                                    try:
                                        csv_bytes = csv_string.encode('shift_jis')
                                    except UnicodeEncodeError:
                                        csv_bytes = csv_string.encode('cp932', errors='replace')
                                    
                                    blob_client_out = container_client.get_blob_client(output_file_path)
                                    blob_client_out.upload_blob(csv_bytes, overwrite=True)
                                    
                                    folder_files_mapping[folder]["validated_files"].append({
                                        "file_name": file_name,
                                        "date_match": match_status,
                                        "csv_day": csv_day_str
                                    })
                                    
                                    folder_files_mapping[folder]["processed_files"].append({
                                        "original_file": file_name,
                                        "output_file": output_filename,
                                        "output_path": output_file_path,
                                        "output_folder": "today" if match_status else "past"
                                    })
                                    
                                    if match_status:
                                        log_msg = f"✓ Folder: {folder}, File: {file_name}, Day: {csv_day_str} (matches {input_day}) → saved to output_folder_today"
                                        logging.info(log_msg)
                                        operation_logs.append(log_msg)
                                    else:
                                        log_msg = f"✗ Folder: {folder}, File: {file_name}, Day: {csv_day_str} (expected {input_day}) → saved to output_folder_past"
                                        logging.info(log_msg)
                                        operation_logs.append(log_msg)
                                        
                                except Exception as write_error:
                                    folder_files_mapping[folder]["validated_files"].append({
                                        "file_name": file_name,
                                        "error": f"Failed to write output: {str(write_error)}"
                                    })
                                    error_msg = f"✗ Error writing file {file_name} in {folder}: {str(write_error)}"
                                    logging.error(error_msg)
                                    operation_logs.append(error_msg)
                            else:
                                error_msg = f"✗ Folder: {folder}, File: {file_name} - 年月日 column not found"
                                logging.warning(error_msg)
                                operation_logs.append(error_msg)
                                folder_files_mapping[folder]["validated_files"].append({
                                    "file_name": file_name,
                                    "date_match": False,
                                    "error": "年月日 column not found"
                                })
                        except Exception as e:
                            error_msg = f"✗ Error reading file {file_name} in {folder}: {str(e)}"
                            logging.error(error_msg)
                            operation_logs.append(error_msg)
                            folder_files_mapping[folder]["validated_files"].append({
                                "file_name": file_name,
                                "error": str(e)
                            })
        
        result = {
            "status": "success",
            "input_file": input_file_xlsx,
            "input_folder": input_folder_path,
            "output_folder_today": output_folder_path_today,
            "output_folder_past": output_folder_path_past,
            "input_day": input_day,
            "xlsx_data": df_xlsx.to_dict(orient="records"),
            "total_patterns_from_xlsx": len(xlsx_patterns),
            "xlsx_patterns": list(sorted(xlsx_patterns)),
            "all_folders_found": list(sorted(folders)),
            "total_folders_found": len(folders),
            "filtered_folders": filtered_folders,
            "total_filtered_folders": len(filtered_folders),
            "folder_files_mapping": folder_files_mapping,
            "operation_logs": operation_logs,
            "message": f"Found {len(filtered_folders)} matching folders from {len(xlsx_patterns)} XLSX patterns out of {len(folders)} total folders"
        }

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in phase1_SD_hc_data_convert: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="phase1/kd_hc_data_convert", methods=["POST"])
def phase1_kd_hc_data_convert(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        container_name = req_body.get("container_name", "external")
        input_file_xlsx = req_body.get("input_file_xlsx")
        input_sheet_name = req_body.get("input_sheet_name")
        input_folder_path = req_body.get("input_folder_path")
        output_folder_path_today = req_body.get("output_folder_path_today")
        output_folder_path_past = req_body.get("output_folder_path_past")
        input_day = req_body.get("input_day")

        if not input_file_xlsx or not input_folder_path or not output_folder_path_today or not output_folder_path_past:
            return func.HttpResponse(
                json.dumps({"error": "input_file_xlsx, input_folder_path, output_folder_path_today, and output_folder_path_past are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)

        blob_client_xlsx = blob_service.get_blob_client(container=container_name, blob=input_file_xlsx)
        xlsx_data = blob_client_xlsx.download_blob().readall()
        df_xlsx = pd.read_excel(
            BytesIO(xlsx_data),
            sheet_name=input_sheet_name,
            header=None,
            dtype=str
        )

        if df_xlsx.empty:
            return func.HttpResponse(
                json.dumps({"error": "XLSX sheet is empty"}),
                status_code=400,
                mimetype="application/json"
            )
        
        xlsx_patterns = set(
            df_xlsx.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda x: x != ""]
        )
        
        container_client = blob_service.get_container_client(container=container_name)
        
        folder_prefix = input_folder_path.strip("/")
        if folder_prefix and not folder_prefix.endswith("/"):
            folder_prefix += "/"
        
        blobs = container_client.list_blobs(name_starts_with=folder_prefix)
        
        folders = set()
        for blob in blobs:
            blob_path = blob.name[len(folder_prefix):]
            if "/" in blob_path:
                folder_name = blob_path.split("/")[0]
                folders.add(folder_name)
        
        filtered_folders = [f for f in folders if f in xlsx_patterns]
        filtered_folders.sort()
        
        folder_files_mapping = {}
        operation_logs = [] 
        
        if input_day:
            file_types = ["ZA.csv", "ZI.csv", "ZK.csv", "ZB.csv"]
            
            for folder in filtered_folders:
                folder_path = f"{folder_prefix}{folder}/"
                found_files = []
                
                blobs_in_folder = container_client.list_blobs(name_starts_with=folder_path)
                
                for blob in blobs_in_folder:
                    blob_name = blob.name.split("/")[-1]
                    if (len(blob_name) >= 15 and 
                        blob_name.startswith("01") and 
                        blob_name[2:10].isdigit() and 
                        any(blob_name.endswith(ft) for ft in file_types)):
                        found_files.append(blob_name)
                
                if found_files:
                    folder_files_mapping[folder] = {
                        "files": sorted(found_files),
                        "validated_files": [],
                        "processed_files": []
                    }
                    
                    try:
                        corp, store = folder.split("_", 1)
                    except ValueError:
                        error_msg = f"✗ Invalid folder format (expected corp_store): {folder}"
                        logging.error(error_msg)
                        operation_logs.append(error_msg)
                        continue
                    
                    for file_name in found_files:
                        file_path = f"{folder_path}{file_name}"
                        try:
                            df_csv = read_csv_from_blob(container_client, file_path)
                            
                            if '年月日' in df_csv.columns:
                                csv_day = df_csv['年月日'].iloc[0] if len(df_csv) > 0 else None
                                csv_day_str = str(csv_day).strip() if csv_day is not None else ""
                                
                                file_type = file_name[-6:-4] + "_KD"
                                name = file_name[-6:-4]

                                schema_columns = CSV_SCHEMAS.get(file_type, [])

                                if schema_columns:
                                    df_output = pd.DataFrame()
                                    input_cols = list(df_csv.columns)
                                    
                                    for idx, schema_col in enumerate(schema_columns):
                                        if schema_col in df_csv.columns:
                                            df_output[schema_col] = df_csv[schema_col]
                                        elif idx < len(input_cols):
                                            df_output[schema_col] = df_csv[input_cols[idx]]
                                        else:
                                            df_output[schema_col] = ''
                                    
                                    df_csv = df_output
                                
                                df_csv.insert(0, '会社コード', corp)
                                df_csv.insert(1, '店舗コード', store)
                                
                                if csv_day_str == input_day:
                                    output_folder = output_folder_path_today
                                    match_status = True
                                else:
                                    output_folder = output_folder_path_past
                                    match_status = False
                                
                                output_filename = f"{corp}{store}{csv_day_str}{name}_2.csv"
                                output_folder_structured = f"{output_folder.strip('/')}/{corp}{store}{csv_day_str}/"
                                output_file_path = f"{output_folder_structured}{output_filename}"
                                
                                try:
                                    csv_string = df_csv.to_csv(index=False)
                                    try:
                                        csv_bytes = csv_string.encode('shift_jis')
                                    except UnicodeEncodeError:
                                        csv_bytes = csv_string.encode('cp932', errors='replace')
                                    
                                    blob_client_out = container_client.get_blob_client(output_file_path)
                                    blob_client_out.upload_blob(csv_bytes, overwrite=True)
                                    
                                    folder_files_mapping[folder]["validated_files"].append({
                                        "file_name": file_name,
                                        "date_match": match_status,
                                        "csv_day": csv_day_str
                                    })
                                    
                                    folder_files_mapping[folder]["processed_files"].append({
                                        "original_file": file_name,
                                        "output_file": output_filename,
                                        "output_path": output_file_path,
                                        "output_folder": "today" if match_status else "past"
                                    })
                                    
                                    if match_status:
                                        log_msg = f"✓ Folder: {folder}, File: {file_name}, Day: {csv_day_str} (matches {input_day}) → saved to output_folder_today"
                                        logging.info(log_msg)
                                        operation_logs.append(log_msg)
                                    else:
                                        log_msg = f"✗ Folder: {folder}, File: {file_name}, Day: {csv_day_str} (expected {input_day}) → saved to output_folder_past"
                                        logging.info(log_msg)
                                        operation_logs.append(log_msg)
                                        
                                except Exception as write_error:
                                    folder_files_mapping[folder]["validated_files"].append({
                                        "file_name": file_name,
                                        "error": f"Failed to write output: {str(write_error)}"
                                    })
                                    error_msg = f"✗ Error writing file {file_name} in {folder}: {str(write_error)}"
                                    logging.error(error_msg)
                                    operation_logs.append(error_msg)
                            else:
                                error_msg = f"✗ Folder: {folder}, File: {file_name} - 年月日 column not found"
                                logging.warning(error_msg)
                                operation_logs.append(error_msg)
                                folder_files_mapping[folder]["validated_files"].append({
                                    "file_name": file_name,
                                    "date_match": False,
                                    "error": "年月日 column not found"
                                })
                        except Exception as e:
                            error_msg = f"✗ Error reading file {file_name} in {folder}: {str(e)}"
                            logging.error(error_msg)
                            operation_logs.append(error_msg)
                            folder_files_mapping[folder]["validated_files"].append({
                                "file_name": file_name,
                                "error": str(e)
                            })
        
        result = {
            "status": "success",
            "input_file": input_file_xlsx,
            "input_folder": input_folder_path,
            "output_folder_today": output_folder_path_today,
            "output_folder_past": output_folder_path_past,
            "input_day": input_day,
            "xlsx_data": df_xlsx.to_dict(orient="records"),
            "total_patterns_from_xlsx": len(xlsx_patterns),
            "xlsx_patterns": list(sorted(xlsx_patterns)),
            "all_folders_found": list(sorted(folders)),
            "total_folders_found": len(folders),
            "filtered_folders": filtered_folders,
            "total_filtered_folders": len(filtered_folders),
            "folder_files_mapping": folder_files_mapping,
            "operation_logs": operation_logs,
            "message": f"Found {len(filtered_folders)} matching folders from {len(xlsx_patterns)} XLSX patterns out of {len(folders)} total folders"
        }

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in phase1_SD_hc_data_convert: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="phase1/dk_hc_data_convert", methods=["POST"])
def phase1_dk_hc_data_convert(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        container_name = req_body.get("container_name", "external")
        input_file_xlsx = req_body.get("input_file_xlsx")
        input_sheet_name = req_body.get("input_sheet_name")
        input_folder_path = req_body.get("input_folder_path")
        output_folder_path_today = req_body.get("output_folder_path_today")
        output_folder_path_past = req_body.get("output_folder_path_past")
        input_day = req_body.get("input_day")

        if not input_file_xlsx or not input_folder_path or not output_folder_path_today or not output_folder_path_past:
            return func.HttpResponse(
                json.dumps({"error": "input_file_xlsx, input_folder_path, output_folder_path_today, and output_folder_path_past are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)

        blob_client_xlsx = blob_service.get_blob_client(container=container_name, blob=input_file_xlsx)
        xlsx_data = blob_client_xlsx.download_blob().readall()
        df_xlsx = pd.read_excel(
            BytesIO(xlsx_data),
            sheet_name=input_sheet_name,
            header=None,
            dtype=str
        )

        if df_xlsx.empty:
            return func.HttpResponse(
                json.dumps({"error": "XLSX sheet is empty"}),
                status_code=400,
                mimetype="application/json"
            )
        
        xlsx_patterns = set(
            df_xlsx.iloc[:, 0]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda x: x != ""]
        )
        
        container_client = blob_service.get_container_client(container=container_name)
        
        folder_prefix = input_folder_path.strip("/")
        if folder_prefix and not folder_prefix.endswith("/"):
            folder_prefix += "/"
        
        blobs = container_client.list_blobs(name_starts_with=folder_prefix)
        
        folders = set()
        for blob in blobs:
            blob_path = blob.name[len(folder_prefix):]
            if "/" in blob_path:
                folder_name = blob_path.split("/")[0]
                folders.add(folder_name)
        
        filtered_folders = [f for f in folders if f in xlsx_patterns]
        filtered_folders.sort()
        
        folder_files_mapping = {}
        operation_logs = [] 
        
        if input_day:
            file_types = ["ZA.csv", "ZI.csv", "ZK.csv", "ZB.csv", "TD.csv", "TP.csv", "TR.csv"]
            
            for folder in filtered_folders:
                folder_path = f"{folder_prefix}{folder}/"
                found_files = []

                blobs_in_folder = container_client.list_blobs(name_starts_with=folder_path)

                for blob in blobs_in_folder:
                    blob_name = blob.name.split("/")[-1]
                    if (len(blob_name) >= 15 and
                        blob_name.startswith("01") and
                        blob_name[2:10].isdigit() and
                        any(blob_name.endswith(ft) for ft in file_types)):
                        found_files.append(blob_name)

                if not found_files:
                    continue

                folder_files_mapping[folder] = {
                    "files": sorted(found_files),
                    "validated_files": [],
                    "processed_files": []
                }

                try:
                    corp, store = folder.split("_", 1)
                except ValueError:
                    error_msg = f"✗ Invalid folder format (expected corp_store): {folder}"
                    logging.error(error_msg)
                    operation_logs.append(error_msg)
                    continue

                for file_name in found_files:
                    file_path = f"{folder_path}{file_name}"

                    try:
                        df_csv = read_csv_from_blob(container_client, file_path)

                        eigyoDay = file_name[2:10]

                        name = file_name[-6:-4]        
                        file_type = name + "_DK"

                        if name == "TD" and corp == "00001" and store in ("00436", "00437"):
                            file_type = "TD_DK_00001_00436_00437"
                        if name == "TD" and corp == "00002" and store == "00703":
                            file_type = "TD_DK_00002_00703"
                        if name in ("TD", "TP", "TR") and corp == "00002" and store == "00708":
                            file_type = f"{name}_DK_00002_00708"
                            
                        use_eigyo_day = name in ["TD", "TP", "TR"]

                        if use_eigyo_day:
                            csv_day_str = eigyoDay
                        else:
                            if '年月日' not in df_csv.columns:
                                raise Exception("年月日 column not found")

                            csv_day = df_csv['年月日'].iloc[0] if len(df_csv) > 0 else None
                            csv_day_str = str(csv_day).strip() if csv_day else ""

                        schema_columns = CSV_SCHEMAS.get(file_type, [])
                        if schema_columns:
                            df_output = pd.DataFrame()
                            input_cols = list(df_csv.columns)
                            
                            for idx, schema_col in enumerate(schema_columns):
                                if schema_col in df_csv.columns:
                                    df_output[schema_col] = df_csv[schema_col]
                                elif idx < len(input_cols):
                                    df_output[schema_col] = df_csv[input_cols[idx]]
                                else:
                                    df_output[schema_col] = ''
                            
                            df_csv = df_output

                        if file_type == "ZI_DK":
                            DATA_TYPE = {
                                "交換数": "decimal2"
                            }

                            df_csv = apply_adf_types(
                                df_csv,
                                DATA_TYPE
                            )

                        if use_eigyo_day:
                            df_csv['会社コード'] = corp
                            df_csv['店舗コード'] = store
                            df_csv['年月日'] = eigyoDay
                        else:
                            df_csv.insert(0, '会社コード', corp)
                            df_csv.insert(1, '店舗コード', store)

                        if csv_day_str == input_day:
                            output_folder = output_folder_path_today
                            match_status = True
                        else:
                            output_folder = output_folder_path_past
                            match_status = False

                        output_filename = f"{corp}{store}{csv_day_str}{name}_2.csv"
                        output_folder_structured = (
                            f"{output_folder.strip('/')}/{corp}{store}{csv_day_str}/"
                        )
                        output_file_path = f"{output_folder_structured}{output_filename}"

                        csv_string = df_csv.to_csv(index=False)
                        try:
                            csv_bytes = csv_string.encode('shift_jis')
                        except UnicodeEncodeError:
                            csv_bytes = csv_string.encode('cp932', errors='replace')

                        blob_client_out = container_client.get_blob_client(output_file_path)
                        blob_client_out.upload_blob(csv_bytes, overwrite=True)

                        folder_files_mapping[folder]["processed_files"].append({
                            "original_file": file_name,
                            "output_file": output_filename,
                            "output_path": output_file_path,
                            "output_folder": "today" if match_status else "past"
                        })

                    except Exception as e:
                        error_msg = f"✗ Error processing file {file_name} in {folder}: {str(e)}"
                        logging.error(error_msg)
                        operation_logs.append(error_msg)
        
        result = {
            "status": "success",
            "input_file": input_file_xlsx,
            "input_folder": input_folder_path,
            "output_folder_today": output_folder_path_today,
            "output_folder_past": output_folder_path_past,
            "input_day": input_day,
            "xlsx_data": df_xlsx.to_dict(orient="records"),
            "total_patterns_from_xlsx": len(xlsx_patterns),
            "xlsx_patterns": list(sorted(xlsx_patterns)),
            "all_folders_found": list(sorted(folders)),
            "total_folders_found": len(folders),
            "filtered_folders": filtered_folders,
            "total_filtered_folders": len(filtered_folders),
            "folder_files_mapping": folder_files_mapping,
            "operation_logs": operation_logs,
            "message": f"Found {len(filtered_folders)} matching folders from {len(xlsx_patterns)} XLSX patterns out of {len(folders)} total folders"
        }

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in phase1_SD_hc_data_convert: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="phase1/check_match_csv", methods=["POST"])
def phase1_check_match_csv(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        container_name = req_body.get("container_name")
        csv_file_path_1 = req_body.get("csv_file_path_1")
        csv_file_path_2 = req_body.get("csv_file_path_2")

        if not container_name or not csv_file_path_1 or not csv_file_path_2:
            return func.HttpResponse(
                json.dumps({
                    "error": "container_name, csv_file_path_1, csv_file_path_2 are required"
                }),
                status_code=400,
                mimetype="application/json"
            )

        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)

        df1 = read_csv_from_blob(container_client, csv_file_path_1)
        df2 = read_csv_from_blob(container_client, csv_file_path_2)

        df1.columns = [unicodedata.normalize('NFKC', str(col)) for col in df1.columns]
        df2.columns = [unicodedata.normalize('NFKC', str(col)) for col in df2.columns]

        row_count_csv1 = len(df1)
        row_count_csv2 = len(df2)
        row_count_match = row_count_csv1 == row_count_csv2

        columns_csv1 = list(df1.columns)
        columns_csv2 = list(df2.columns)

        columns_only_in_csv1 = sorted(list(set(columns_csv1) - set(columns_csv2)))
        columns_only_in_csv2 = sorted(list(set(columns_csv2) - set(columns_csv1)))

        diff_detail = {}

        common_columns = set(columns_csv1).intersection(set(columns_csv2))
        min_rows = min(row_count_csv1, row_count_csv2)

        for col in common_columns:
            s1 = df1[col].iloc[:min_rows]
            s2 = df2[col].iloc[:min_rows]

            diff_rows = (s1 != s2) & ~(s1.isna() & s2.isna())
            if diff_rows.any():
                diff_detail[col] = diff_rows[diff_rows].index.tolist()

        match = (
            row_count_match
            and not columns_only_in_csv1
            and not columns_only_in_csv2
            and not diff_detail
        )

        return func.HttpResponse(
            json.dumps({
                "match": match,
                "row_count": {
                    "csv1": row_count_csv1,
                    "csv2": row_count_csv2,
                    "match": row_count_match
                },
                "columns_only_in_csv1": columns_only_in_csv1,
                "columns_only_in_csv2": columns_only_in_csv2,
                "diff_detail": diff_detail
            }, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({
                "error": str(e)
            }, ensure_ascii=False),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="phase1/check_match_hc_data_conv", methods=["POST"])
def phase1_check_match_hc_data_conv(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()

        container_name = req_body.get("container_name")
        source_folder_path = req_body.get("source_folder_path")
        target_folder_path = req_body.get("target_folder_path")
        output_folder_path = req_body.get("output_folder_path")

        if not all([container_name, source_folder_path, target_folder_path, output_folder_path]):
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameters"}),
                status_code=400,
                mimetype="application/json"
            )

        # ---- Blob client ----
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)

        matched_files = []
        not_matched_files = []

        # ---- Walk source folders ----
        source_prefixes = container_client.walk_blobs(
            name_starts_with=source_folder_path.rstrip("/") + "/",
            delimiter="/"
        )

        for prefix in source_prefixes:
            if not prefix.name.endswith("/"):
                continue

            folder_name = prefix.name.rstrip("/").split("/")[-1]  # {Corp}{Store}{yyyymmdd}

            # ---- List files in source folder ----
            source_files = container_client.list_blobs(name_starts_with=prefix.name)

            for src_blob in source_files:
                src_file_name = os.path.basename(src_blob.name)

                # only check files start with 0000
                if not src_file_name.startswith("0000") or not src_file_name.endswith(".csv"):
                    continue

                try:
                    corp = folder_name[:5]
                    store = folder_name[5:10]

                    target_blob_path = (
                        f"{target_folder_path.rstrip('/')}/"
                        f"{corp}_{store}/xml/{folder_name}/{src_file_name}"
                    )

                    # ---- Read CSVs ----
                    df_src = read_csv_from_blob(container_client, src_blob.name)
                    df_tgt = read_csv_from_blob(container_client, target_blob_path)

                    # ---- Sort for stable comparison ----
                    df_src = df_src.sort_values(by=list(df_src.columns)).reset_index(drop=True)
                    df_tgt = df_tgt.sort_values(by=list(df_tgt.columns)).reset_index(drop=True)

                    # ---- Shape check ----
                    if df_src.shape != df_tgt.shape:
                        not_matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path,
                            "reason": "Shape mismatch",
                            "detail": {
                                "source_shape": df_src.shape,
                                "target_shape": df_tgt.shape
                            }
                        })
                        continue

                    # ---- Cell-by-cell check ----
                    mismatches = []

                    for r in range(df_src.shape[0]):
                        for c in range(df_src.shape[1]):
                            src_val = df_src.iat[r, c]
                            tgt_val = df_tgt.iat[r, c]

                            if str(src_val) != str(tgt_val):
                                mismatches.append({
                                    "row": r,
                                    "column": str(df_src.columns[c]),
                                    "source_value": src_val,
                                    "target_value": tgt_val
                                })

                    if mismatches:
                        not_matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path,
                            "reason": "Value mismatch",
                            "total_mismatches": len(mismatches),
                            "details": mismatches
                        })
                    else:
                        matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path
                        })

                except Exception as e:
                    not_matched_files.append({
                        "source_file": src_blob.name,
                        "target_file": target_blob_path if 'target_blob_path' in locals() else "",
                        "reason": "ERROR",
                        "detail": {
                            "message": str(e)
                        }
                    })

        # ---- Result JSON ----
        result_json = {
            "summary": {
                "total_files_checked": len(matched_files) + len(not_matched_files),
                "matched": len(matched_files),
                "not_matched": len(not_matched_files)
            },
            "matched_files": matched_files,
            "not_matched_files": not_matched_files
        }

        # ---- Output file name (no timestamp) ----
        source_folder_name = source_folder_path.rstrip("/").split("/")[-2]
        output_file_name = f"hc_data_conv_check_{source_folder_name}.json"
        output_blob_path = f"{output_folder_path.rstrip('/')}/{output_file_name}"

        blob_client_out = container_client.get_blob_client(output_blob_path)
        blob_client_out.upload_blob(
            json.dumps(result_json, ensure_ascii=False, indent=2),
            overwrite=True
        )

        return func.HttpResponse(
            json.dumps({
                "message": "Check completed",
                "output_file": output_blob_path,
                "summary": result_json["summary"]
            }, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="phase1/check_match_csv_out", methods=["POST"])
def phase1_check_match_csv_out(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()

        container_name = req_body.get("container_name")
        source_folder_path = req_body.get("source_folder_path")
        target_folder_path = req_body.get("target_folder_path")
        output_folder_path = req_body.get("output_folder_path")

        TIMESTAMP_COLUMNS = ["作成日時", "データ更新時刻"]

        if not all([container_name, source_folder_path, target_folder_path, output_folder_path]):
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameters"}),
                status_code=400,
                mimetype="application/json"
            )

        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)

        matched_files = []
        not_matched_files = []

        source_prefixes = container_client.walk_blobs(
            name_starts_with=source_folder_path.rstrip("/") + "/",
            delimiter="/"
        )

        for prefix in source_prefixes:
            if not prefix.name.endswith("/"):
                continue

            folder_name = prefix.name.rstrip("/").split("/")[-1]

            if len(folder_name) < 18:
                continue

            corp = folder_name[:5]
            store = folder_name[5:10]

            source_files = container_client.list_blobs(name_starts_with=prefix.name)

            for src_blob in source_files:
                src_file_name = os.path.basename(src_blob.name)

                if src_file_name.startswith("0000") or not src_file_name.endswith(".csv"):
                    continue

                target_blob_path = (
                    f"{target_folder_path.rstrip('/')}/"
                    f"{corp}_{store}/xml/{folder_name}/{src_file_name}"
                )

                try:
                    df_src = read_csv_from_blob(container_client, src_blob.name)
                    df_tgt = read_csv_from_blob(container_client, target_blob_path)

                    cols_to_drop_src = [c for c in TIMESTAMP_COLUMNS if c in df_src.columns]
                    cols_to_drop_tgt = [c for c in TIMESTAMP_COLUMNS if c in df_tgt.columns]

                    df_src = df_src.drop(columns=cols_to_drop_src)
                    df_tgt = df_tgt.drop(columns=cols_to_drop_tgt)

                    df_src = df_src.sort_values(by=list(df_src.columns)).reset_index(drop=True)
                    df_tgt = df_tgt.sort_values(by=list(df_tgt.columns)).reset_index(drop=True)

                    if df_src.shape != df_tgt.shape:
                        not_matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path,
                            "reason": "Shape mismatch",
                            "detail": {
                                "source_shape": df_src.shape,
                                "target_shape": df_tgt.shape
                            }
                        })
                        continue

                    mismatches = []

                    for r in range(df_src.shape[0]):
                        for c in range(df_src.shape[1]):
                            src_val = df_src.iat[r, c]
                            tgt_val = df_tgt.iat[r, c]

                            if str(src_val) != str(tgt_val):
                                mismatches.append({
                                    "row": r,
                                    "column": str(df_src.columns[c]),
                                    "source_value": src_val,
                                    "target_value": tgt_val
                                })

                    if mismatches:
                        not_matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path,
                            "reason": "Value mismatch",
                            "total_mismatches": len(mismatches),
                            "details": mismatches
                        })
                    else:
                        matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path
                        })

                except Exception as e:
                    not_matched_files.append({
                        "source_file": src_blob.name,
                        "target_file": target_blob_path,
                        "reason": "ERROR",
                        "detail": {
                            "message": str(e)
                        }
                    })

        result_json = {
            "summary": {
                "total_files_checked": len(matched_files) + len(not_matched_files),
                "matched": len(matched_files),
                "not_matched": len(not_matched_files)
            },
            "matched_files": matched_files,
            "not_matched_files": not_matched_files
        }

        source_folder_name = source_folder_path.rstrip("/").split("/")[-2]
        output_file_name = f"csv_out_check_{source_folder_name}.json"
        output_blob_path = f"{output_folder_path.rstrip('/')}/{output_file_name}"

        blob_client_out = container_client.get_blob_client(output_blob_path)
        blob_client_out.upload_blob(
            json.dumps(result_json, ensure_ascii=False, indent=2),
            overwrite=True
        )

        return func.HttpResponse(
            json.dumps({
                "message": "Check completed",
                "output_file": output_blob_path,
                "summary": result_json["summary"]
            }, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="phase1/check_match_all", methods=["POST"])
def phase1_check_match_all(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()

        container_name = req_body.get("container_name")
        source_folder_path = req_body.get("source_folder_path")
        target_folder_path = req_body.get("target_folder_path")
        output_folder_path = req_body.get("output_folder_path")

        TIMESTAMP_COLUMNS = ["作成日時", "データ更新時刻"]

        if not all([container_name, source_folder_path, target_folder_path, output_folder_path]):
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameters"}),
                status_code=400,
                mimetype="application/json"
            )

        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)

        matched_files = []
        not_matched_files = []

        source_prefixes = container_client.walk_blobs(
            name_starts_with=source_folder_path.rstrip("/") + "/",
            delimiter="/"
        )

        for prefix in source_prefixes:
            if not prefix.name.endswith("/"):
                continue

            folder_name = prefix.name.rstrip("/").split("/")[-1]

            if len(folder_name) < 18:
                continue

            corp = folder_name[:5]
            store = folder_name[5:10]

            source_files = container_client.list_blobs(name_starts_with=prefix.name)

            for src_blob in source_files:
                src_file_name = os.path.basename(src_blob.name)

                if not src_file_name.endswith(".csv"):
                    continue

                target_blob_path = (
                    f"{target_folder_path.rstrip('/')}/"
                    f"{corp}_{store}/xml/{folder_name}/{src_file_name}"
                )

                try:
                    df_src = read_csv_from_blob(container_client, src_blob.name)
                    df_tgt = read_csv_from_blob(container_client, target_blob_path)

                    cols_to_drop_src = [c for c in TIMESTAMP_COLUMNS if c in df_src.columns]
                    cols_to_drop_tgt = [c for c in TIMESTAMP_COLUMNS if c in df_tgt.columns]

                    df_src = df_src.drop(columns=cols_to_drop_src)
                    df_tgt = df_tgt.drop(columns=cols_to_drop_tgt)

                    df_src = df_src.sort_values(by=list(df_src.columns)).reset_index(drop=True)
                    df_tgt = df_tgt.sort_values(by=list(df_tgt.columns)).reset_index(drop=True)

                    src_columns = list(df_src.columns)
                    tgt_columns = list(df_tgt.columns)

                    if src_columns != tgt_columns:
                        not_matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path,
                            "reason": "Schema mismatch",
                            "detail": {
                                "source_columns": src_columns,
                                "target_columns": tgt_columns,
                                "missing_in_target": list(set(src_columns) - set(tgt_columns)),
                                "extra_in_target": list(set(tgt_columns) - set(src_columns))
                            }
                        })
                        continue

                    if df_src.shape != df_tgt.shape:
                        not_matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path,
                            "reason": "Shape mismatch",
                            "detail": {
                                "source_shape": df_src.shape,
                                "target_shape": df_tgt.shape
                            }
                        })
                        continue

                    mismatches = []

                    for r in range(df_src.shape[0]):
                        if len(mismatches) >= 3:
                            break
                        for c in range(df_src.shape[1]):
                            src_val = df_src.iat[r, c]
                            tgt_val = df_tgt.iat[r, c]

                            if str(src_val) != str(tgt_val):
                                mismatches.append({
                                    "row": r,
                                    "column": str(df_src.columns[c]),
                                    "source_value": src_val,
                                    "target_value": tgt_val
                                })

                                if len(mismatches) >= 10:
                                    break

                    if mismatches:
                        not_matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path,
                            "reason": "Value mismatch",
                            "total_mismatches": len(mismatches),
                            "details": mismatches
                        })
                    else:
                        matched_files.append({
                            "source_file": src_blob.name,
                            "target_file": target_blob_path
                        })

                except Exception as e:
                    not_matched_files.append({
                        "source_file": src_blob.name,
                        "target_file": target_blob_path,
                        "reason": "ERROR",
                        "detail": {
                            "message": str(e)
                        }
                    })

        result_json = {
            "summary": {
                "total_files_checked": len(matched_files) + len(not_matched_files),
                "matched": len(matched_files),
                "not_matched": len(not_matched_files)
            },
            "matched_files": matched_files,
            "not_matched_files": not_matched_files
        }

        source_folder_name = source_folder_path.rstrip("/").split("/")[-2]
        output_file_name = f"check_match_{source_folder_name}.json"
        output_blob_path = f"{output_folder_path.rstrip('/')}/{output_file_name}"

        blob_client_out = container_client.get_blob_client(output_blob_path)
        blob_client_out.upload_blob(
            json.dumps(result_json, ensure_ascii=False, indent=2),
            overwrite=True
        )

        return func.HttpResponse(
            json.dumps({
                "message": "Check completed",
                "output_file": output_blob_path,
                "summary": result_json["summary"]
            }, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

def schema_csv_out(schema_key, sum_csv_df):
    schema_columns = CSV_SCHEMAS.get(schema_key, [])
        
    if schema_columns:
        df_output = pd.DataFrame()
        input_cols = list(sum_csv_df.columns)
        
        for idx, schema_col in enumerate(schema_columns):
            if schema_col in sum_csv_df.columns:
                df_output[schema_col] = sum_csv_df[schema_col]
            elif idx < len(input_cols):
                df_output[schema_col] = sum_csv_df[input_cols[idx]]
            else:
                df_output[schema_col] = ''
        
        sum_csv_df = df_output

    return sum_csv_df

def apply_adf_types(df: pd.DataFrame, type_map: dict) -> pd.DataFrame:
    for col, dtype in type_map.items():
        if col not in df.columns:
            continue

        if dtype == "decimal2":
            df[col] = (
                pd.to_numeric(df[col], errors="coerce")
                .map(lambda x: f"{x:.2f}" if pd.notna(x) else "")
            )
        elif dtype == "decimal3":
            df[col] = (
                pd.to_numeric(df[col], errors="coerce")
                .map(lambda x: f"{x:.3f}" if pd.notna(x) else "")
            )
        elif dtype == "decimal5":
            df[col] = (
                pd.to_numeric(df[col], errors="coerce")
                .map(lambda x: f"{x:.5f}" if pd.notna(x) else "")
            )
        elif dtype == "int":
            df[col] = (
                pd.to_numeric(df[col], errors="coerce")
                .map(lambda x: (
                    str(
                        int(
                            Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                        )
                    ) if pd.notna(x) else ""
                ))
            )

    return df

@app.route(route="phase1/csv_out", methods=["POST"])
def phase1_csv_out(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        container_name = req_body.get("container_name")
        input_folder_path = req_body.get("input_folder_path")
        output_folder_path = req_body.get("output_folder_path")

        if not container_name or not input_folder_path or not output_folder_path:
            return func.HttpResponse(
                json.dumps({
                    "error": "container_name, input_folder_path, and output_folder_path are required"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)

        folder_prefix = input_folder_path.strip("/")
        if folder_prefix and not folder_prefix.endswith("/"):
            folder_prefix += "/"
        
        blobs = container_client.list_blobs(name_starts_with=folder_prefix)
        
        level1_folders = set()
        for blob in blobs:
            blob_path = blob.name[len(folder_prefix):]
            if "/" in blob_path:
                level1_folder = blob_path.split("/")[0]
                level1_folders.add(level1_folder)
        
        filtered_folders = sorted([f for f in level1_folders if f.startswith("0000")])

        sum_files = ["sum_BLOCK_REPORT.csv", "sum_CURRENT_BLOCK.csv", "sum_CURRENT_COUNT.csv",
                     "sum_CURRENT_KISYU.csv", "sum_NIPPOU_FILE.csv", "sum_S_RATE_TOTAL.csv",
                     "sum_TEMPO_MODE.csv", "sum_TEMPO_REPORT.csv", "sum_TEMPO_SYSTEM_MODE.csv",
                     "sum_YUUGI_FILE.csv"]
        sum_dfs = {}
        sum_file_stats = {}

        for file_name in sum_files:
            blob_path = f"{folder_prefix}{file_name}" 
            try:
                df = read_csv_from_blob(container_client, blob_path)

                sum_file_stats[file_name] = {
                    "exists": True,
                    "rows": int(df.shape[0]),
                    "columns": int(df.shape[1]),
                    "column_names": list(df.columns)
                }

                sum_dfs[file_name] = df

            except Exception as e:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to read {file_name}",
                        "detail": str(e)
                    }, ensure_ascii=False),
                    status_code=500
                )

        # Process sum_BLOCK_REPORT.csv
        sum_block_report_df = sum_dfs["sum_BLOCK_REPORT.csv"]
        schema_key = "sum_BLOCK_REPORT"
        sum_block_report_df = schema_csv_out(schema_key, sum_block_report_df)
        DATA_TYPE = {
            "推定景品金額": "decimal2",
            "粗利景品金額": "decimal2",
            "推定粗利景品金額": "decimal2",
            "粗利金額": "decimal2",
            "推定粗利金額": "decimal2",
        }

        sum_block_report_df = apply_adf_types(
            sum_block_report_df,
            DATA_TYPE
        )
        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_block_report_df[
                sum_block_report_df["店舗コード"] == store_code
            ]

            columns_to_select = [
                "ブロック番号",
                "遊技台台数",
                "台間現金売上金庫",
                "台間現金売上",
                "台間カード売上",
                "金庫売上",
                "リプレイ金額",
                "リプレイ玉数",
                "景品金額",
                "景品玉数",
                "推定景品金額",
                "推定景品玉数",
                "粗利景品金額",
                "推定粗利景品金額",
                "粗利金額",
                "推定粗利金額",
                "累計アウト",
                "累計セーフ",
                "台間券売機売上",
                "台間券売機売上金庫"
            ]
            
            if store_df.empty:
                store_df = pd.DataFrame(columns=columns_to_select)
            else:
                store_df = store_df[columns_to_select]
                store_df = store_df.sort_values(by="ブロック番号", ascending=True)
            
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/BLOCK_REPORT.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write BLOCK_REPORT.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        # Process sum.CURRENT_BLOCK.csv
        sum_current_block_df = sum_dfs["sum_CURRENT_BLOCK.csv"]
        schema_key = "sum_CURRENT_BLOCK"
        sum_current_block_df = schema_csv_out(schema_key, sum_current_block_df)
        DATA_TYPE = {
            "貸出換算率": "decimal3",
            "返却換算率": "decimal3",
            "リプレイ手数料": "int"
        }

        sum_current_block_df = apply_adf_types(
            sum_current_block_df,
            DATA_TYPE
        )

        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_current_block_df[
                sum_current_block_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            columns_to_select = [
                "ブロック番号",
                "名称",
                "貸出換算率",
                "返却換算率",
                "ＰＡＳ区分",
                "リプレイ手数料",
                "ＸＭＬ口座番号"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]
            
            store_df = store_df.rename(columns={
                "名称": "ブロック名称",
                "ＰＡＳ区分": "PAS区分",
                "ＸＭＬ口座番号": "口座番号"
            })
            
            store_df = store_df.sort_values(by="ブロック番号", ascending=True)
            
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/CURRENT_BLOCK.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write CURRENT_BLOCK.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )

        # Process sum_CURRENT_COUNT.csv
        sum_current_count_df = sum_dfs["sum_CURRENT_COUNT.csv"]
        schema_key = "sum_CURRENT_COUNT"
        sum_current_count_df = schema_csv_out(schema_key, sum_current_count_df)
        DATA_TYPE = {
            "主返却換算率": "decimal3",
            "従返却換算率": "decimal3",
            "主返却換算比率": "decimal3",
            "貸出換算率計算値": "int",
            "リプレイ手数料": "int"
        }

        sum_current_count_df = apply_adf_types(
            sum_current_count_df,
            DATA_TYPE
        )

        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_current_count_df[
                sum_current_count_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            columns_to_select = [
                "ＸＭＬ口座番号",
                "ＰＡＳ区分",
                "貸出換算率入力値金額",
                "貸出換算率入力値個数",
                "貸出換算率計算値",
                "主返却換算率",
                "従返却換算率",
                "主返却換算比率",
                "リプレイ手数料"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]
            
            store_df = store_df.rename(columns={
                "ＸＭＬ口座番号": "口座番号",
                "ＰＡＳ区分": "PAS区分"
            })
            
            store_df = store_df.sort_values(by="口座番号", ascending=True)
            
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/CURRENT_COUNT.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write CURRENT_COUNT.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        # Process sum_CURRENT_KISYU.csv
        sum_current_kisyu_df = sum_dfs["sum_CURRENT_KISYU.csv"]
        schema_key = "sum_CURRENT_KISYU"
        sum_current_kisyu_df = schema_csv_out(schema_key, sum_current_kisyu_df)
        
        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_current_kisyu_df[
                sum_current_kisyu_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            if "ＸＭＬ機種グループコード" in store_df.columns:
                store_df["ＸＭＬ機種グループコード"] = (
                    store_df["ＸＭＬ機種グループコード"].astype(str).str[-2:]
                )

            if "登録日付" in store_df.columns:
                store_df["登録日付"] = pd.to_datetime(
                    store_df["登録日付"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")
                store_df["登録日付"] = store_df["登録日付"].fillna("")

            store_df["タイプ"] = "0"

            columns_to_select = [
                "ＸＭＬ機種コード",
                "ブロック番号",
                "ＸＭＬ機種名称",
                "ＸＭＬ機種グループコード",
                "表示有効フラグ",
                "登録日付",
                "アウトスピード稼働時間算出用",
                "アウトスピード回転率算出用",
                "賞球数1",
                "賞球数2",
                "賞球数3",
                "賞球数4",
                "賞球数5",
                "ＰＡＳ区分",
                "タイプ",
                "設置台数"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]

            store_df = store_df.rename(columns={
                "ＸＭＬ機種コード": "機種コード",
                "ＸＭＬ機種名称": "機種名称",
                "ＸＭＬ機種グループコード": "機種グループコード",
                "ＰＡＳ区分": "PAS区分"
            })
            
            store_df = store_df.sort_values(by=["設置台数", "PAS区分"], ascending=True).reset_index(drop=True)
            
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/CURRENT_KISYU.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write CURRENT_KISYU.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        # Process sum_NIPPOU_FILE.csv
        sum_nippou_file_df = sum_dfs["sum_NIPPOU_FILE.csv"]
        schema_key = "sum_NIPPOU_FILE"
        sum_nippou_file_df = schema_csv_out(schema_key, sum_nippou_file_df)
        
        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_nippou_file_df[
                sum_nippou_file_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            columns_to_select = [
                "口座番号",
                "計数機貯玉件数",
                "計数機貯玉数",
                "預券発行件数",
                "預券発行数",
                "預券読込件数",
                "預券読込数",
                "手入力件数",
                "手入力数",
                "貯玉引落件数",
                "貯玉引落数",
                "景品払出数",
                "余玉数",
                "拾玉数",
                "未回収保留券件数",
                "未回収保留券数",
                "貯玉追加数",
                "会員預券読込件数",
                "会員預券読込数",
                "会員手入力件数",
                "会員手入力数",
                "会員貯玉引落件数",
                "会員貯玉引落数",
                "会員自販機利用数",
                "会員景品払出数",
                "会員貯玉追加数",
                "非会員預券読込件数",
                "非会員預券読込数",
                "非会員手入力件数",
                "非会員手入力数",
                "非会員自販機利用数",
                "非会員景品払出数",
                "非会員余玉数",
                "非会員拾玉数",
                "未回収預券件数",
                "未回収預券数",
                "保留券発行件数",
                "保留券発行数",
                "保留券読込件数",
                "保留券読込数",
                "前回貯玉残数",
                "貯玉訂正件数",
                "貯玉訂正数",
                "口座清算数",
                "会員削除件数",
                "会員削除",
                "POS 引落数",
                "再プレイ利用人数",
                "再プレイ利用数",
                "再プレイ手数料数",
                "当日貯玉残数",
                "出庫合計",
                "G 景品",
                "一般景品",
                "その他景品",
                "会員売上人数",
                "会員売上金額",
                "非会員売上件数",
                "非会員売上金額",
                "会員交換人数",
                "会員交換金額",
                "非会員交換件数",
                "非会員交換金額"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]
            
            store_df = store_df.rename(columns={
                "POS 引落数": "POS引落数",
                "G 景品": "G景品"
            })
            
            store_df = store_df.sort_values(by="口座番号", ascending=True).reset_index(drop=True)
            
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/NIPPOU_FILE.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write NIPPOU_FILE.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        # Process sum_S_RATE_TOTAL.csv
        sum_s_rate_total_df = sum_dfs["sum_S_RATE_TOTAL.csv"]
        schema_key = "sum_S_RATE_TOTAL"
        sum_s_rate_total_df = schema_csv_out(schema_key, sum_s_rate_total_df)
        
        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_s_rate_total_df[
                sum_s_rate_total_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            columns_to_select = [
                "ブロック番号",
                "データ日付＿テキスト",
                "稼働",
                "開店閉店フラグ"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]
            
            store_df = store_df.rename(columns={
                "データ日付＿テキスト": "日時",
                "稼働": "稼働数"
            })
                        
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/S_RATE_TOTAL.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write S_RATE_TOTAL.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        # Process sum_TEMPO_MODE.csv
        sum_tempo_mode_df = sum_dfs["sum_TEMPO_MODE.csv"]
        schema_key = "sum_TEMPO_MODE"
        sum_tempo_mode_df = schema_csv_out(schema_key, sum_tempo_mode_df)
        
        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_tempo_mode_df[
                sum_tempo_mode_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            for col, fmt in [
                ("処理年月日", "%Y-%m-%d %H:%M:%S"),
                ("データ日付", "%Y-%m-%d"),
                ("作成日時", "%Y-%m-%d %H:%M:%S"),
                ("店舗システム営業日付", "%Y-%m-%d"),
                ("IN系営業日付", "%Y-%m-%d"),
                ("OUT系営業日付", "%Y-%m-%d")
            ]:
                if col in store_df.columns:
                    store_df[col] = pd.to_datetime(store_df[col], errors="coerce").dt.strftime(fmt)
                    store_df[col] = store_df[col].fillna("")

            columns_to_select = [
                "エリアコード",
                "店舗コード",
                "データ日付",
                "店舗名称",
                "システムバージョン",
                "作成日時",
                "店舗システム営業日付",
                "IN系営業日付",
                "OUT系営業日付",
                "店舗システム動作モード",
                "IN系システム動作モード",
                "OUT系システム動作モード"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]
            
            store_df = store_df.rename(columns={
                "システムバージョン": "店舗システムバージョン",
            })
                        
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/TEMPO_MODE.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write TEMPO_MODE.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        # Process sum_TEMPO_REPORT.csv
        sum_tempo_report_df = sum_dfs["sum_TEMPO_REPORT.csv"]
        schema_key = "sum_TEMPO_REPORT"
        sum_tempo_report_df = schema_csv_out(schema_key, sum_tempo_report_df)
        DATA_TYPE = {
            "消費税率": "decimal5"
        }

        sum_tempo_report_df = apply_adf_types(
            sum_tempo_report_df,
            DATA_TYPE
        )
        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_tempo_report_df[
                sum_tempo_report_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            for col, fmt in [
                ("開店時刻", "%Y-%m-%d %H:%M:%S"),
                ("閉店時刻", "%Y-%m-%d %H:%M:%S"),
                ("業務開始時刻", "%Y-%m-%d %H:%M:%S"),
                ("業務終了時刻", "%Y-%m-%d %H:%M:%S"),
                ("時計変更時刻", "%Y-%m-%d %H:%M:%S"),
                ("記憶消去時刻", "%Y-%m-%d %H:%M:%S"),
                ("電源投入時刻", "%Y-%m-%d %H:%M:%S"),
                ("データ更新時刻", "%Y-%m-%d %H:%M:%S")
            ]:
                if col in store_df.columns:
                    store_df[col] = pd.to_datetime(store_df[col], errors="coerce").dt.strftime(fmt)
                    store_df[col] = store_df[col].fillna("")

            if "消費税率" in store_df.columns:
                store_df["消費税率"] = (
                    pd.to_numeric(store_df["消費税率"], errors="coerce")
                    .astype("Int64")
                    .astype(str)
                    .str.zfill(2)
                    .replace("<NA>", "")
                )

            columns_to_select = [
                "開店時刻",
                "閉店時刻",
                "業務開始時刻",
                "業務終了時刻",
                "消費税率",
                "P 台数",
                "S 台数",
                "開店前アウト",
                "開店前セーフ",
                "開店前景品合計金額",
                "開店前金庫売上合計金額",
                "開店前台間売上合計金額",
                "時計変更時刻",
                "記憶消去時刻",
                "電源投入時刻",
                "データ更新時刻",
                "券売機売上合計金額",
                "K1 精算機合計金額1",
                "K1 精算機合計金額2",
                "プレミア合計金額",
                "店休日モード"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]
            
            store_df = store_df.rename(columns={
                "P 台数": "P台数",
                "S 台数": "S台数",
                "K1 精算機合計金額1": "K1精算機合計金額1",
                "K1 精算機合計金額2": "K1精算機合計金額2"
            })
            
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/TEMPO_REPORT.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write TEMPO_REPORT.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        # Process sum_TEMPO_SYSTEM_MODE.csv
        sum_tempo_system_mode_df = sum_dfs["sum_TEMPO_SYSTEM_MODE.csv"]
        schema_key = "sum_TEMPO_SYSTEM_MODE"
        sum_tempo_system_mode_df = schema_csv_out(schema_key, sum_tempo_system_mode_df)
        DATA_TYPE = {
            "消費税率": "decimal5"
        }

        sum_tempo_report_df = apply_adf_types(
            sum_tempo_report_df,
            DATA_TYPE
        )

        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_tempo_system_mode_df[
                sum_tempo_system_mode_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            columns_to_select = [
                "INDB確定",
                "OUTDB確定",
                "在庫確定",
                "強制DB更新",
                "手動送信"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]
                        
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/TEMPO_SYSTEM_MODE.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write TEMPO_SYSTEM_MODE.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        # Process sum_YUUGI_FILE.csv
        sum_yuugi_file_df = sum_dfs["sum_YUUGI_FILE.csv"]
        schema_key = "sum_YUUGI_FILE"
        sum_yuugi_file_df = schema_csv_out(schema_key, sum_yuugi_file_df)
        DATA_TYPE = {
            "A": "decimal2",
            "B": "decimal2",
            "C": "decimal2",
            "D": "decimal2",
            "E": "decimal2",
            "F": "decimal2",
            "G": "decimal2",
            "H": "decimal2",
            "J": "decimal2",
            "K": "decimal2",
            "ベース": "decimal2",
            "回転率": "decimal2",
            "A_F": "int",
            "B_F": "int",
            "C_F": "int",
            "D_F": "int",
            "E_F": "int",
            "F_F": "int",
            "G_F": "int",
            "H_F": "int",
            "J_F": "int",
            "K_F": "int",
            "推定景品": "int",
            "粗利推定景品": "int"
        }

        sum_yuugi_file_df = apply_adf_types(
            sum_yuugi_file_df,
            DATA_TYPE
        )
        
        for folder in filtered_folders:
            if len(folder) < 10:
                continue

            store_code = folder[5:10]
            
            store_df = sum_yuugi_file_df[
                sum_yuugi_file_df["店舗コード"] == store_code
            ]

            if store_df.empty:
                continue

            fixed_columns = ["個別確認１", "測定日", "個別確認２"]

            for col in fixed_columns:
                store_df[col] = "0"

            columns_to_select = [
                "ＸＭＬ台番",
                "機種",
                "コーナ",
                "ブロック",
                "設定",
                "個別確認１",
                "測定日",
                "A",
                "A_F",
                "B",
                "B_F",
                "C",
                "C_F",
                "D",
                "D_F",
                "E",
                "E_F",
                "F",
                "F_F",
                "G",
                "G_F",
                "H",
                "H_F",
                "J",
                "J_F",
                "K",
                "K_F",
                "R_セーフ",
                "R_アウト",
                "R_通常中セーフ",
                "R_通常中アウト",
                "R_確変中セーフ",
                "R_確変中アウト",
                "R_特賞",
                "R_確変",
                "R_特賞3",
                "R_通常中スタート",
                "R_確変中スタート",
                "R_通常中入賞",
                "稼働",
                "打止",
                "最終アウト",
                "最終スタート",
                "R_特賞中手持ち",
                "R_現金売上",
                "R_カード売上",
                "R_リプレイ金額",
                "R_現金売上断線",
                "R_カード売上断線",
                "R_リプレイ断線",
                "R_金枠開閉",
                "R_木枠開閉",
                "磁石不正",
                "R_幕板開閉",
                "P台遊技ステータス",
                "点検発生済みF",
                "R_入賞",
                "R_RB 中払出",
                "R_RB 中投入",
                "最大差",
                "最小差",
                "ベース",
                "回転率",
                "平均特賞中手持ち",
                "推定景品",
                "粗利推定景品",
                "R_券売機売上",
                "R_券売機売上断線",
                "R_確変中入賞",
                "R_通常中大入賞",
                "R_特賞中大入賞",
                "R_通常中入賞2",
                "R_時短中セーフ",
                "R_時短中アウト",
                "R_時短中スタート",
                "最終ゲーム数2",
                "P台遊技ステータス2",
                "R_スタート",
                "R_時短",
                "R_特賞中アウト",
                "R_特賞中セーフ",
                "R_突確中アウト",
                "R_突確中セーフ",
                "R_特賞中スタート",
                "R_通常中スタートB",
                "R_確変中スタートB",
                "R_時短中スタートB",
                "R_突確",
                "R_確中当り",
                "R_確変中入賞２",
                "R_確変中大入賞",
                "R_時短中入賞",
                "R_時短中入賞２",
                "R_時短中大入賞",
                "不正２",
                "R_時中当り",
                "個別確認２",
                "最大放出数"
            ]
            
            existing_cols = [c for c in columns_to_select if c in store_df.columns]
            store_df = store_df[existing_cols]
            
            store_df = store_df.rename(columns={
                "ＸＭＬ台番": "台番",
                "個別確認１": "釘マーク",
                "R_RB 中払出": "R_RB中払出",
                "R_RB 中投入": "R_RB中投入",
                "R_確変中入賞２":"R_確変中入賞2",
                "R_時短中入賞２":"R_時短中入賞2",
                "不正２": "不正2",
                "個別確認２": "釘マーク2"
            })
            
            store_df = store_df.sort_values(by="台番", ascending=True)
            
            output_blob_path = (
                f"{output_folder_path.strip('/')}/"
                f"{folder}/YUUGI_FILE.csv"
            )

            try:
                csv_string = store_df.to_csv(index=False)
                try:
                    csv_bytes = csv_string.encode('shift_jis')
                except UnicodeEncodeError:
                    csv_bytes = csv_string.encode('cp932', errors='replace')
                
                blob_client_out = container_client.get_blob_client(output_blob_path)
                blob_client_out.upload_blob(csv_bytes, overwrite=True)

            except Exception as write_error:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Failed to write YUUGI_FILE.csv for folder {folder}",
                        "detail": str(write_error)
                    }, ensure_ascii=False),
                    status_code=500
                )
        
        result = {
            "input_folder_path": input_folder_path,
            "output_folder_path": output_folder_path,
            "filtered_folders": filtered_folders,
            "total_filtered_folders": len(filtered_folders),
            "sum_files": sum_file_stats
        }
        
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({
                "error": str(e)
            }, ensure_ascii=False),
            status_code=500,
            mimetype="application/json"
        )

# def join_hc_mst_inner(zi_df, hc_mst_lookup):
#     result_rows = []

#     for _, zi_row in zi_df.iterrows():
#         key = (
#             zi_row["会社コード"],
#             zi_row["店舗コード"],
#             zi_row["種別略称"]
#         )

#         zi_date = zi_row["営業日"]

#         for item in hc_mst_lookup.get(key, []):
#             if item["適用開始日"] <= zi_date <= item["適用終了日"]:
#                 merged = zi_row.to_dict()
#                 merged.update(item["row"].to_dict())
#                 result_rows.append(merged)
#                 break  

#     return pd.DataFrame(result_rows)

# @app.route(route="phase1/sd_db_in_05", methods=["POST"])
# def phase1_sd_db_in_05(req: func.HttpRequest) -> func.HttpResponse:
#     try:
#         req_body = req.get_json()
#         container_name = req_body.get("container_name")
#         xlsx_input_file_path = req_body.get("xlsx_input_file_path")
#         folder_input_path = req_body.get("folder_input_path")
#         folder_output_path = req_body.get("folder_output_path")

#         if not container_name or not xlsx_input_file_path or not folder_input_path or not folder_output_path:
#             return func.HttpResponse(
#                 json.dumps({
#                     "error": "container_name, xlsx_input_file_path, folder_input_path, and folder_output_path are required"
#                 }),
#                 status_code=400,
#                 mimetype="application/json"
#             )
        
#         connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
#         blob_service = BlobServiceClient.from_connection_string(connection_string)
#         container_client = blob_service.get_container_client(container_name)

#         blob_client_xlsx = container_client.get_blob_client(xlsx_input_file_path)
#         xlsx_data = blob_client_xlsx.download_blob().readall()
#         xlsx_hc_mst = pd.read_excel(BytesIO(xlsx_data), sheet_name='HC変換マスタ', dtype=object)
#         xlsx_hc_mst_mukou_kouza_nf = pd.read_excel(BytesIO(xlsx_data), sheet_name='無効口座マスタ_口座別業務日報', dtype=object)

#         mukou_kouza_lookup = {}

#         for _, row in xlsx_hc_mst_mukou_kouza_nf.iterrows():
#             key = (
#                 row["会社コード"],
#                 row["店舗コード"]
#             )
#             mukou_kouza_lookup[key] = row

#         hc_mst_lookup = defaultdict(list)

#         for _, row in xlsx_hc_mst.iterrows():
#             key = (
#                 row["会社コード"],
#                 row["店舗コード"],
#                 row["種別略称"]
#             )

#             hc_mst_lookup[key].append({
#                 "適用開始日": row["適用開始日"],
#                 "適用終了日": row["適用終了日"],
#                 "row": row
#             })

#         folder_prefix = folder_input_path.strip("/")
#         if folder_prefix and not folder_prefix.endswith("/"):
#             folder_prefix += "/"
        
#         blobs = container_client.list_blobs(name_starts_with=folder_prefix)
        
#         zi_csv_files = []

#         pattern = re.compile(
#             rf"^{re.escape(folder_prefix)}[^/]+/[^/]*ZI_2\.csv$"
#         )

#         for blob in blobs:
#             blob_name = blob.name
#             if pattern.match(blob_name):
#                 zi_csv_files.append(blob_name)
                
        
#         for zi_blob_path in zi_csv_files:
#             try:
#                 zi_df = read_csv_from_blob(container_client, zi_blob_path)

#                 zi_df["営業日"] = (
#                     zi_df["年月日"].str.slice(0, 4) + "-" +
#                     zi_df["年月日"].str.slice(4, 6) + "-" +
#                     zi_df["年月日"].str.slice(6, 8)
#                 )

#                 zi_df_join_hc_mst = join_hc_mst_inner(zi_df, hc_mst_lookup)

#                 zero_columns = [
#                     "計数機貯玉件数","計数機貯玉数","預券発行件数","預券読込件数","預券読込数",
#                     "手入力件数","手入力数","貯玉引落件数","貯玉引落数","景品払出数","余玉数",
#                     "拾玉数","未回収保留券件数","未回収保留券数","貯玉追加数",
#                     "会員預券読込件数","会員預券読込数","会員手入力件数","会員手入力数",
#                     "会員貯玉引落件数","会員貯玉引落数","会員自販機利用数",
#                     "会員景品払出数","会員貯玉追加数",
#                     "非会員預券読込件数","非会員預券読込数","非会員手入力件数","非会員手入力数",
#                     "非会員自販機利用数","非会員景品払出数","非会員余玉数","非会員拾玉数",
#                     "未回収預券件数","未回収預券数",
#                     "保留券発行件数","保留券発行数","保留券読込件数","保留券読込数",
#                     "前回貯玉残数","貯玉訂正件数","貯玉訂正数","口座清算数",
#                     "会員削除件数","会員削除","POS引落数",
#                     "再プレイ利用人数","再プレイ手数料数",
#                     "当日貯玉残数","出庫合計","G景品","一般景品","その他景品",
#                     "会員売上人数","会員売上金額",
#                     "非会員売上件数","会員交換人数","会員交換金額",
#                     "非会員交換件数","非会員交換金額"
#                 ]
                
#                 zi_df[zero_columns] = 0

#                 zi_df["口座番号"] = to_long(zi_df["有効口座"])

#                 zi_df_agg = (
#                     zi_df
#                     .groupby(["会社コード", "店舗コード"], as_index=False)
#                     .agg(
#                         ダミー=("会社コード", "count")
#                     )
#                 )

#                 zi_df_agg = zi_df_agg[["会社コード", "店舗コード"]]


#         return func.HttpResponse(
#             json.dumps({
#                 "zi_csv_files_found": zi_csv_files,
#                 "total_zi_csv_files": len(zi_csv_files)
#             }, ensure_ascii=False),
#             status_code=200,
#             mimetype="application/json"
#         )
#     except Exception as e:
#         return func.HttpResponse(
#             json.dumps({
#                 "error": str(e)
#             }, ensure_ascii=False),
#             status_code=500,
#             mimetype="application/json"
#         )

# =====================================#
# XML check and delete function API    #
# =====================================#    

@app.function_name(name="xml_check_delete")
@app.route(route="xml_check_delete", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def xml_check_delete_function(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to check and delete XML files based on lookup
    """
    logging.info('Python HTTP trigger function processed a request for xml_check.')
    
    try:
    
        # Get day parameter
        day_param = req.params.get('day')
        if not day_param:
            try: 
                req_body = req.get_json()
                day_param = req_body.get('day')
            except ValueError:
                raise ValueError("'day' parameter is required.") 
        
        if len(day_param) != 8:
            raise ValueError("day must be in YYYYMMDD format")
        # Process XML check and deletion
        result_no_dk = xml_check_delete(day_param, '店舗一覧_DK')
        result_no_kd = xml_check_delete(day_param, '店舗一覧_KD')
        result_no_sd = xml_check_delete(day_param, '店舗一覧_SD')
        result_no_ma = xml_check_delete(day_param, '店舗一覧_MA')

        return func.HttpResponse(
            f"XML check and deletion completed for day: {day_param}. {result_no_dk}, {result_no_kd}, {result_no_sd}, {result_no_ma}",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error in xml_check_function: {str(e)}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )
    
# =====================================#
# CSV data put function API            #
# =====================================#    

@app.function_name(name="csv_data_put")
@app.route(route="csv_data_put", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def csv_data_put_function(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to copy CSV data based on domain and day
    """
    logging.info('Python HTTP trigger function processed a request for csv_data_put.')
    
    try:
        # Get parameters
        day_param = req.params.get('day')
        
        if not day_param:
            try:
                req_body = req.get_json()
                day_param = day_param or req_body.get('day')
            except ValueError:
                pass 
        
        if not day_param:
            raise ValueError("'day' parameter is required.")
        
        if len(day_param) != 8:
            raise ValueError("day must be in YYYYMMDD format")
        
        # Get blob storage settings from environment variables
        connection_string = os.environ.get('AzureWebJobsStorage')
        if not connection_string:
            raise ValueError("AzureWebJobsStorage is not configured")
        container_name = os.environ.get('STORAGE_CONTAINER_NAME', 'external')
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Process CSV data put
        # Copy Data For DK
        csv_data_put(day_param, DomainEnum.DK, container_name, blob_service_client)
        # Copy Data For KD
        csv_data_put(day_param, DomainEnum.KD, container_name, blob_service_client)
        # Copy Data For SD
        csv_data_put(day_param, DomainEnum.SD, container_name, blob_service_client)
        # Copy Data For MA
        csv_data_put(day_param, DomainEnum.MA, container_name, blob_service_client)
        
        return func.HttpResponse(
            f"CSV data put completed for day: {day_param}",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error in csv_data_put_function: {str(e)}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )

# =====================================#
# XML existence check function API     #
# =====================================#

@app.function_name(name="xml_exist_check")
@app.route(route="xml_exist_check", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def xml_exist_check_function(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to check existence of XML files based on lookup
    """
    logging.info('Python HTTP trigger function processed a request for xml_exist_check.')
    
    try:
        # Get day parameter
        day_param = req.params.get('day')
        if not day_param:
            try:
                req_body = req.get_json()
                day_param = req_body.get('day')
            except ValueError:
                raise ValueError("'day' parameter is required.") 
        
        if len(day_param) != 8:
            raise ValueError("day must be in YYYYMMDD format")

        # Process XML existence check
        exists = xml_exist_check(day_param)
        
        if not exists:
            return func.HttpResponse(
                f"XML files are missing for day: {day_param}",
                status_code=404
            )
        
        return func.HttpResponse(
            f"XML existence check completed for day: {day_param}. All files exist: {exists}",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error in xml_exist_check_function: {str(e)}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )
    
# ------------------------------------------------MAIN FUNCTION -----------------------------

# OTHER VARIABLES
class DomainEnum(Enum): 
    DK = "DK"
    KD = "KD"
    SD = "SD"
    MA = "MA"

# ===================================== #
# XML check and delete function API    #
# =====================================#

def xml_check_delete(
        day: str, 
        sheet_name: str
    ): 
    conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('STORAGE_CONTAINER_NAME')
    base_path = os.getenv('BASE_PATH')
    lookup_file = os.getenv('LOOKUP_FILE_PATH')

    logging.info("Begin initializing BlobServiceClient")
    blob_service = BlobServiceClient.from_connection_string(conn_str)
    logging.info(f"Account name: {blob_service.account_name}")

    container = blob_service.get_container_client(
        container_name, )
    logging.info(f"Accessed container: {container_name}")

    # 1. list subfolders
    subfolders = set() 
    day_path = f"{base_path}/{day}/"
    logging.info(f"Listing blobs with prefix: {day_path}")

    for blob in container.list_blobs(name_starts_with=day_path): 
        logging.info(f"Found blob: {blob.name}")
        folder_name = blob.name[len(day_path):len(day_path)+11]
        subfolders.add(folder_name)

    logging.info(f"Found subfolders: {subfolders}")

    # 2. lookup excel 
    blob = container.get_blob_client(lookup_file)
    logging.info(f"Downloading lookup file from: {lookup_file}")
    try:
        data = blob.download_blob().readall()
    except Exception as e:
        logging.error(f"Failed to download lookup file: {lookup_file}")
        raise
    logging.info("Lookup file downloaded successfully")

    lookup_df = pd.read_excel(
            io.BytesIO(data),
            sheet_name=sheet_name,
            dtype=str, 
            header=None
    )
    logging.info(f"Lookup file read into DataFrame successfully {lookup_df.shape[0]} rows found")
    valid_text = ",".join(lookup_df.iloc[:,0].astype(str))
    logging.info(f"Valid codes from lookup with sheet {sheet_name}: {valid_text}")
    filtered = [subfolder for subfolder in subfolders if subfolder in valid_text]
    logging.info(f"Filtered subfolders to delete: {filtered}")
    deleted = []

    # initial Data Lake Client 
    service_client = DataLakeServiceClient.from_connection_string(conn_str)
    file_system_client = service_client.get_file_system_client(container_name)

    for item in filtered: 
        target = item[:5] + "_" + item[6:11]
        directory_path = f"{day_path}{target}/"

        try: 
            directory_client = file_system_client.get_directory_client(directory_path)
            logging.info(f"Deleting directory: {directory_path}")
            directory_client.delete_directory(recursive=True)
            deleted.append(target)
            logging.info(f"Deleted directory: {directory_path}")

        except Exception as e:
            logging.error(f"Failed to delete directory: {directory_path}. Error: {str(e)}")

    return {
        "input_day": day, 
        "matched": filtered,
        "deleted_files": deleted
    }

# =====================================#
# CSV data put function logic          #
# =====================================#

def csv_data_put(
    day: str, 
    domain: DomainEnum, 
    container_name: str, 
    blob_service_client: BlobServiceClient
): 
    logging.info(f"Starting csv_data_put for day: {day}, domain: {domain.value}")
    container_client = blob_service_client.get_container_client(container_name)
    
    DOMAIN_SOURCE_PATH = {
        DomainEnum.DK: "ダイコクHC/当日データ/",
        DomainEnum.KD: "北電子HC/当日データ/",
        DomainEnum.SD: "三幸電子HC/当日データ/",
        DomainEnum.MA: "マースHC/当日データ/",
    }
    
    if domain not in DOMAIN_SOURCE_PATH: 
        raise ValueError(f"Unsupported domain: {domain}")

    source_base_path = DOMAIN_SOURCE_PATH[domain]
    src_prefix = f"HC連携/{source_base_path}"

    blobs = container_client.list_blobs(name_starts_with=src_prefix)

    copied = 0 
    for blob in blobs: 
        file_name = blob.name.split('/')[-1] 

        if not file_name.endswith('.csv') or not file_name.startswith('0000'): 
            continue

        folder_name = blob.name[len(src_prefix):len(src_prefix)+18]
        logging.info(f"Processing blob: {blob.name}, folder_name: {folder_name}")

        des_folder_name = f"{folder_name[:5]}_{folder_name[5:10]}"
        logging.info(f"Destination folder name: {des_folder_name}")
       
        dest_blob_path = (
            f"HC連携/テスト/dynam/send/"
            f"{day}/" 
            f"{des_folder_name}/"
            f"xml/"
            f"{folder_name}/"
            f"{file_name}"
        )
        logging.info(f"Destination blob path: {''.join(dest_blob_path)}")

        # Get Blob Clients
        src_blob_client = container_client.get_blob_client(blob)
        dest_blob_client = container_client.get_blob_client(dest_blob_path)

        # Use Server-Side Copy instead of Download/Upload
        # This is much faster as data stays within the Azure network
        dest_blob_client.start_copy_from_url(src_blob_client.url)
        
        logging.info(f"Initiated server-side copy to {dest_blob_path}")
        copied += 1

    return {
        "domain": domain.value,
        "day": day, 
        "copied_files": copied, 
        "count": copied
    }

# =====================================#
# XML existence check function API     #
# =====================================#

def xml_exist_check(
    day: str
): 
    conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('STORAGE_CONTAINER_NAME')
    base_path = os.getenv('BASE_PATH')
    lookup_file = os.getenv('LOOKUP_FILE_PATH')
    
    logging.info("Begin initializing BlobServiceClient")
    blob_service = BlobServiceClient.from_connection_string(conn_str)
    
    container = blob_service.get_container_client(container_name)
    logging.info(f"Accessed container: {container_name}")

    day_path = f"{base_path}/{day}/"


    # Load lookup
    lookup_blob = container.get_blob_client(lookup_file)
    logging.info(f"Downloading lookup file from: {lookup_file}")
    lookup_data = lookup_blob.download_blob().readall()
    logging.info("Lookup file downloaded successfully")
    lookup_df = pd.read_excel(
        io.BytesIO(lookup_data),
        sheet_name="店舗一覧_全店",
        dtype=str
    )
    logging.info(f"Lookup file read into DataFrame successfully {lookup_df.shape[0]} rows found")
    valid_codes = ",".join(lookup_df.iloc[:,0].astype(str))

    logging.info(f"Valid codes from lookup: {valid_codes}")

    

    for blob in container.list_blobs(name_starts_with=day_path):
        relative = blob.name[len(day_path):]
        parts = relative.split("/") 
        store_folder = parts[0]

        if store_folder not in valid_codes:
            continue

        found_JISSEKI = False
        store_prefix = f"{day_path}{store_folder}/xml/"
        
        for subfolder_blob in container.list_blobs(name_starts_with=store_prefix):
            filename = subfolder_blob.name.split("/")[-1]
            if filename.startswith("JISSEKI_") and filename.endswith(".dynam"):
                logging.info(f"Found JISSEKI file: {filename} in {store_folder}")
                found_JISSEKI = True
                break

        if not found_JISSEKI:
            logging.warning(f"Missing JISSEKI file for store: {store_folder}")
            return False
    
    return True