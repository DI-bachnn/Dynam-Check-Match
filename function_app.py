import azure.functions as func
from azure.storage.blob import BlobServiceClient
from io import StringIO
import pandas as pd
import logging

app = func.FunctionApp()

@app.function_name(name="checkMatch20251030")
@app.route(route="checkMatch20251030", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def checkMatch20251030(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logging.info("checkMatchPremium called")
    
    output_lines = []

    def log(line: str):
        output_lines.append(line)

    try:
        connection_string = "DefaultEndpointsProtocol=https;AccountName=dwhdeast02strg001dev;AccountKey=maM+BH0McLmG8xcEUe23CrkS95tkaj5gcRAbfOUZ7rDQQbsvSiJPVLA3Alv2tlyJAlUnx0kATgjJAThrKYNusw==;EndpointSuffix=core.windows.net"
        container_name = "external" 
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        folder_none = f"HC連携/benchmark/none/20251030"
        folder_second_try = f"HC連携/benchmark/second_try/20251030"

        blobs_none = list(container_client.list_blobs(name_starts_with=folder_none))

        folders_con = set()
        for blob in blobs_none:
            parts = blob.name.split('/')
            if len(parts) >= 6:
                folders_con.add((parts[4], parts[5]))

        for folder1, folder2 in folders_con:
            prefix_none = f"{folder_none}/{folder1}/{folder2}/"
            prefix_second = f"{folder_second_try}/{folder1}/{folder2}/"

            csvs_none = [b for b in blobs_none if b.name.startswith(prefix_none) and b.name.endswith(".csv")]

            for blob_none in csvs_none:
                csv_name = blob_none.name.split('/')[-1]
                blob_second_name = f"{prefix_second}{csv_name}"
                file_path_display = f"{folder1}/{folder2}/{csv_name}"

                try:
                    blob_none_client = container_client.get_blob_client(blob_none.name)
                    blob_second_client = container_client.get_blob_client(blob_second_name)

                    df_none = read_csv_with_jp_encoding(blob_none_client)
                    df_second = read_csv_with_jp_encoding(blob_second_client)

                except Exception as e:
                    log(f"❌ {file_path_display}")
                    log(f"    Cannot read file: {e}")
                    continue

                df_none_sorted = df_none.sort_values(by=list(df_none.columns)).reset_index(drop=True)
                df_second_sorted = df_second.sort_values(by=list(df_second.columns)).reset_index(drop=True)

                rows_none, cols_none = df_none_sorted.shape
                rows_second, cols_second = df_second_sorted.shape

                # rows_none, cols_none = df_none.shape
                # rows_second, cols_second = df_second.shape

                if rows_none == rows_second and cols_none == cols_second and df_none_sorted.equals(df_second_sorted):
                # if rows_none == rows_second and cols_none == cols_second and df_none.equals(df_second):
                    log(f"✔ {file_path_display}")
                    log(f"    [{rows_none}]x[{cols_none}] - Data matches exactly")
                else:
                    TIMESTAMP_COLUMNS = ["作成日時", "データ更新時刻"]
                    try:
                        diff = df_none.compare(df_second)
                        if (
                            len(df_none) == 1
                            and set(diff.columns.get_level_values(0)) <= set(TIMESTAMP_COLUMNS)
                        ):
                            log(f"✔ {file_path_display}")
                            log(f"    [{rows_none}]x[{cols_none}] - Ignored because only timestamp differs ({', '.join(set(diff.columns.get_level_values(0)))})")
                            continue
                    except:
                        pass

                    log(f"❌ {file_path_display}")
                    if rows_none != rows_second or cols_none != cols_second:
                        log(f"    Different dimensions: none=[{rows_none}x{cols_none}], second=[{rows_second}x{cols_second}]")
                    else:
                        log(f"    Same dimensions: [{rows_none}]x[{cols_none}]")

                    log("    Cell values differ")
                    try:
                        diff = df_none.compare(df_second)
                        num_diff_rows = diff.index.nunique()
                        log(f"    Total different rows: {num_diff_rows}")
                        log("    Example of different cells:")
                        log(str(diff.head()))
                    except:
                        log("    Cannot compare dataframes")
        
        result_blob_path = f"HC連携/benchmark/check-match-20251030.txt"
        blob_client = container_client.get_blob_client(result_blob_path)
        blob_client.upload_blob("\n".join(output_lines), overwrite=True)
        print("✅ Result uploaded to blob:", result_blob_path)

    except Exception as e:
        err_text = f"❌ Overall error: {e}"
        log(err_text)
        return func.HttpResponse("\n".join(output_lines), status_code=500, mimetype="text/plain")

    return func.HttpResponse("\n".join(output_lines), mimetype="text/plain")

@app.function_name(name="checkMatch20251023")
@app.route(route="checkMatch20251023", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def checkMatch20251023(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logging.info("checkMatchPremium called")
    
    output_lines = []

    def log(line: str):
        output_lines.append(line)

    try:
        connection_string = "DefaultEndpointsProtocol=https;AccountName=dwhdeast02strg001dev;AccountKey=maM+BH0McLmG8xcEUe23CrkS95tkaj5gcRAbfOUZ7rDQQbsvSiJPVLA3Alv2tlyJAlUnx0kATgjJAThrKYNusw==;EndpointSuffix=core.windows.net"
        container_name = "external" 
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        folder_none = f"HC連携/benchmark/none/20251023"
        folder_second_try = f"HC連携/benchmark/second_try/20251023"

        blobs_none = list(container_client.list_blobs(name_starts_with=folder_none))

        folders_con = set()
        for blob in blobs_none:
            parts = blob.name.split('/')
            if len(parts) >= 6:
                folders_con.add((parts[4], parts[5]))

        for folder1, folder2 in folders_con:
            prefix_none = f"{folder_none}/{folder1}/{folder2}/"
            prefix_second = f"{folder_second_try}/{folder1}/{folder2}/"

            csvs_none = [b for b in blobs_none if b.name.startswith(prefix_none) and b.name.endswith(".csv")]

            for blob_none in csvs_none:
                csv_name = blob_none.name.split('/')[-1]
                blob_second_name = f"{prefix_second}{csv_name}"
                file_path_display = f"{folder1}/{folder2}/{csv_name}"

                try:
                    blob_none_client = container_client.get_blob_client(blob_none.name)
                    blob_second_client = container_client.get_blob_client(blob_second_name)

                    df_none = read_csv_with_jp_encoding(blob_none_client)
                    df_second = read_csv_with_jp_encoding(blob_second_client)

                except Exception as e:
                    log(f"❌ {file_path_display}")
                    log(f"    Cannot read file: {e}")
                    continue

                df_none_sorted = df_none.sort_values(by=list(df_none.columns)).reset_index(drop=True)
                df_second_sorted = df_second.sort_values(by=list(df_second.columns)).reset_index(drop=True)

                rows_none, cols_none = df_none_sorted.shape
                rows_second, cols_second = df_second_sorted.shape

                if rows_none == rows_second and cols_none == cols_second and df_none_sorted.equals(df_second_sorted):
                    log(f"✔ {file_path_display}")
                    log(f"    [{rows_none}]x[{cols_none}] - Data matches exactly")
                else:
                    TIMESTAMP_COLUMNS = ["作成日時", "データ更新時刻"]
                    try:
                        diff = df_none.compare(df_second)
                        if (
                            len(df_none) == 1
                            and set(diff.columns.get_level_values(0)) <= set(TIMESTAMP_COLUMNS)
                        ):
                            log(f"✔ {file_path_display}")
                            log(f"    [{rows_none}]x[{cols_none}] - Ignored because only timestamp differs ({', '.join(set(diff.columns.get_level_values(0)))})")
                            continue
                    except:
                        pass

                    log(f"❌ {file_path_display}")
                    if rows_none != rows_second or cols_none != cols_second:
                        log(f"    Different dimensions: none=[{rows_none}x{cols_none}], second=[{rows_second}x{cols_second}]")
                    else:
                        log(f"    Same dimensions: [{rows_none}]x[{cols_none}]")

                    log("    Cell values differ")
                    try:
                        diff = df_none.compare(df_second)
                        num_diff_rows = diff.index.nunique()
                        log(f"    Total different rows: {num_diff_rows}")
                        log("    Example of different cells:")
                        log(str(diff.head()))
                    except:
                        log("    Cannot compare dataframes")
        
        result_blob_path = f"HC連携/benchmark/check-match-20251023.txt"
        blob_client = container_client.get_blob_client(result_blob_path)
        blob_client.upload_blob("\n".join(output_lines), overwrite=True)
        print("✅ Result uploaded to blob:", result_blob_path)

    except Exception as e:
        err_text = f"❌ Overall error: {e}"
        log(err_text)
        return func.HttpResponse("\n".join(output_lines), status_code=500, mimetype="text/plain")

    return func.HttpResponse("\n".join(output_lines), mimetype="text/plain")

def read_csv_with_jp_encoding(blob_client):
    stream = blob_client.download_blob().readall()
    for enc in ["shift_jis", "cp932"]:
        try:
            text = stream.decode(enc)
            df = pd.read_csv(StringIO(text))
            return df
        except Exception:
            pass
    raise Exception("Cannot read CSV with Japanese encodings (shift_jis, cp932)")