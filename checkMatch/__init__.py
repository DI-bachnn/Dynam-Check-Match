import azure.functions as func
from azure.storage.blob import BlobServiceClient
from io import StringIO
import pandas as pd

# ==============================
# Hàm tiện ích
# ==============================
def read_csv_with_jp_encoding(blob_client):
    stream = blob_client.download_blob().readall()
    for enc in ["shift_jis", "cp932"]:
        try:
            text = stream.decode(enc)
            df = pd.read_csv(StringIO(text))
            return df
        except Exception:
            pass
    raise Exception("Không đọc được CSV với các encoding Nhật (shift_jis, cp932, utf-8)")

# ==============================
# Hàm chính HTTP trigger
# ==============================
def checkMatchData(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    output_lines = []
    logger = context.logger

    def log(line: str):
        print(line, flush=True)     # <-- log ra console
        output_lines.append(line)

    try:
        # ======= Cấu hình Blob =======
        connection_string = "DefaultEndpointsProtocol=https;AccountName=dwhdeast02strg001dev;AccountKey=maM+BH0McLmG8xcEUe23CrkS95tkaj5gcRAbfOUZ7rDQQbsvSiJPVLA3Alv2tlyJAlUnx0kATgjJAThrKYNusw==;EndpointSuffix=core.windows.net"
        container_name = "external" 
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        folder_none = "HC連携/benchmark/none/20251030"
        folder_second_try = "HC連携/benchmark/second_try/20251030"

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
                    log(f"    Không đọc được file: {e}")
                    continue

                rows_none, cols_none = df_none.shape
                rows_second, cols_second = df_second.shape

                if rows_none == rows_second and cols_none == cols_second and df_none.equals(df_second):
                    log(f"✔ {file_path_display}")
                    log(f"    [{rows_none}]x[{cols_none}] - Dữ liệu giống nhau hoàn toàn")
                else:
                    TIMESTAMP_COLUMNS = ["作成日時", "データ更新時刻"]
                    try:
                        diff = df_none.compare(df_second)
                        if (
                            len(df_none) == 1
                            and set(diff.columns.get_level_values(0)) <= set(TIMESTAMP_COLUMNS)
                        ):
                            log(f"✔ {file_path_display}")
                            log(f"    [{rows_none}]x[{cols_none}] - Bỏ qua vì chỉ khác timestamp ({', '.join(set(diff.columns.get_level_values(0)))})")
                            continue
                    except:
                        pass

                    log(f"❌ {file_path_display}")
                    if rows_none != rows_second or cols_none != cols_second:
                        log(f"    Kích thước khác: none=[{rows_none}x{cols_none}], second=[{rows_second}x{cols_second}]")
                    else:
                        log(f"    Cùng kích thước: [{rows_none}]x[{cols_none}]")

                    log("    Khác dữ liệu ở các cell")
                    try:
                        diff = df_none.compare(df_second)
                        num_diff_rows = diff.index.nunique()
                        log(f"    Tổng số dòng khác nhau: {num_diff_rows}")
                        log("    Các cell khác ví dụ:")
                        log(str(diff.head()))
                    except:
                        log("    Không thể compare dataframe")

    except Exception as e:
        err_text = f"❌ Lỗi tổng: {e}"
        log(err_text)
        return func.HttpResponse("\n".join(output_lines), status_code=500, mimetype="text/plain")

    # Trả kết quả HTTP
    return func.HttpResponse("\n".join(output_lines), mimetype="text/plain")
