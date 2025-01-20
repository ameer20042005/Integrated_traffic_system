import os
import cv2
import pandas as pd
from fast_alpr import ALPR
from openpyxl import load_workbook
import tkinter as tk
from tkinter import messagebox
import threading

# تحقق من وجود الفيديو
video_path = "video_2025-01-18_20-27-35.mp4"
if not os.path.exists(video_path):
    print(f"Error: Video file not found at {video_path}")
    exit()

# تحقق من وجود ملف Excel الأول (حفظ الأرقام المكتشفة)
excel_path_1 = "detected_numbers.xlsx"
if not os.path.exists(excel_path_1):
    print(f"Error: Excel file not found at {excel_path_1}")
    exit()

# تحقق من وجود ملف Excel الثاني (معلومات الأرقام)
excel_path_2 = "car_info.xlsx"
if not os.path.exists(excel_path_2):
    print(f"Error: Excel file not found at {excel_path_2}")
    exit()

# قراءة ملف Excel الأول (لحفظ الأرقام المكتشفة)
wb_1 = load_workbook(excel_path_1)
ws_1 = wb_1.active

# قراءة ملف Excel الثاني (معلومات الأرقام)
wb_2 = load_workbook(excel_path_2)
ws_2 = wb_2.active

# تهيئة ALPR
alpr = ALPR(
    detector_model="yolo-v9-t-384-license-plate-end2end",
    ocr_model="global-plates-mobile-vit-v2-model",
)

# فتح الفيديو
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

# دالة للتحقق إذا كان رقم اللوحة موجود في ملف Excel الأول
def is_plate_number_exist(plate_number):
    for row in ws_1.iter_rows(min_row=2, max_row=ws_1.max_row, min_col=1, max_col=1):
        if row[0].value == plate_number:
            return True
    return False

# دالة للتحقق إذا كان رقم اللوحة موجود في ملف Excel الثاني
def get_car_info(plate_number):
    for row in ws_2.iter_rows(min_row=2, max_row=ws_2.max_row, min_col=1, max_col=1):
        if row[0].value == plate_number:  # تحقق من الرقم في العمود الأول
            # إرجاع كافة المعلومات من الأعمدة الأخرى بعد الرقم
            return [ws_2.cell(row=row[0].row, column=col).value for col in range(2, ws_2.max_column + 1)]
    return None

# دالة لحفظ الرقم في ملف Excel الأول
def save_plate_number(plate_number):
    # تحقق إذا كان الرقم موجود مسبقًا في الملف
    if not is_plate_number_exist(plate_number):
        last_row = ws_1.max_row + 1
        ws_1[f"A{last_row}"] = plate_number
        wb_1.save(excel_path_1)
        print(f"The number has been saved.={plate_number}")
    else:
        print(f"The number is available={plate_number}")

# متغير لتخزين النافذة
info_window = None

# دالة لإنشاء أو تحديث نافذة المعلومات
def update_car_info_window(info):
    global info_window
    if info_window is None:
        # إنشاء نافذة جديدة
        info_window = tk.Toplevel()
        info_window.title("Car Information")
        info_window.geometry("400x300")

        # إضافة العناوين للأعمدة
        label = tk.Label(info_window, text="Car Information")
        label.grid(row=0, column=1)

    # إذا كانت المعلومات فارغة (رقم اللوحة غير موجود)، إظهار رسالة
    if info is None:
        info = ["The number is not available"]

    # تحديث البيانات في الأعمدة
    for widget in info_window.winfo_children():
        widget.destroy()  # إزالة جميع العناصر السابقة

    # تحديث المحتوى بناءً على البيانات الجديدة
    for idx, data in enumerate(info, start=1):
        label = tk.Label(info_window, text=data)
        label.grid(row=1, column=idx)

# دالة لعرض الفيديو ومعالجة التنبؤات
def process_video():
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                # إعادة تشغيل الفيديو عند انتهائه
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # الكشف عن اللوحات
            alpr_results = alpr.predict(frame)
            # استخراج الرقم وإضافته إلى متغير
            detected_plate_number = None

            for result in alpr_results:
                if hasattr(result, "ocr"):
                    detected_plate_number = result.ocr.text
                    break  # إيقاف التكرار إذا كنت تحتاج فقط إلى أول رقم

            # طباعة المتغير للتأكد
            print(f"Detected Plate Number: {detected_plate_number}")

            if detected_plate_number:
                # حفظ الرقم في ملف Excel الأول فقط إذا لم يكن موجودًا
                save_plate_number(detected_plate_number)

                # الحصول على المعلومات من ملف Excel الثاني
                car_info = get_car_info(detected_plate_number)

                # تحديث نافذة المعلومات مع البيانات الجديدة أو عرض "The number is not available"
                update_car_info_window(car_info)

            # رسم التنبؤات على الإطار
            annotated_frame = alpr.draw_predictions(frame)

            # عرض الفيديو مع التنبؤات
            cv2.imshow("ALPR Video", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):  # إيقاف الفيديو عند الضغط على 'q'
                break

    except Exception as e:
        print(f"Error during processing: {e}")

    finally:
        # تحرير الموارد
        cap.release()
        cv2.destroyAllWindows()

# دالة لتشغيل واجهة Tkinter
def run_tkinter():
    main_window = tk.Tk()
    main_window.withdraw()  # إخفاء النافذة الرئيسية
    main_window.mainloop()

# تشغيل Tkinter في Thread منفصل
thread_tkinter = threading.Thread(target=run_tkinter)
thread_tkinter.daemon = True  # جعلها تعمل كـ daemon
thread_tkinter.start()

# تشغيل الفيديو ومعالجة التنبؤات
process_video()

print("تم إيقاف تشغيل الفيديو.")
