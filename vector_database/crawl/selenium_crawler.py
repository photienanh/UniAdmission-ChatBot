from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import os

def setup_driver():
    """Thiết lập Chrome driver với các options cần thiết"""
    options = Options()
    options.add_argument('--headless')  # Chạy ẩn để nhanh hơn
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-web-security')
    
    driver = webdriver.Chrome(options=options)
    return driver

def crawl_university_details(driver, row, university_name):
    """Crawl đầy đủ thông tin chi tiết của một trường"""
    try:
        # Click để mở chi tiết
        expand_button = row.find_element(By.CLASS_NAME, "TableContentRow-HpOAv")
        driver.execute_script("arguments[0].click();", expand_button)
        
        # Đợi chi tiết load với timeout
        time.sleep(1.5)
        
        try:
            detail_section = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "DetailUniversity-i6aHx"))
            )
            
            university_details = {
                'basicInfo': {},
                'admissionInfo': {},
                'universityMajors': []
            }
            
            # 1. Lấy thông tin cơ bản
            try:
                info_section = detail_section.find_element(By.CLASS_NAME, "DetailUniversity-WQ1jp")
                
                # Tên trường
                try:
                    university_details['basicInfo']['name'] = info_section.find_element(By.TAG_NAME, "h2").text.strip()
                except:
                    university_details['basicInfo']['name'] = university_name
                
                # Các thông tin khác
                info_rows = info_section.find_elements(By.CLASS_NAME, "DetailUniversity-kCidD")
                for info_row in info_rows:
                    try:
                        label_elem = info_row.find_element(By.CLASS_NAME, "DetailUniversity-wVz3B")
                        value_elem = info_row.find_element(By.CLASS_NAME, "DetailUniversity-iZXCX")
                        
                        label = label_elem.text.strip().rstrip(':').lower()
                        value = value_elem.text.strip()
                        
                        if 'viết tắt' in label or 'acronym' in label:
                            university_details['basicInfo']['acronym'] = value
                        elif 'địa chỉ' in label or 'address' in label:
                            university_details['basicInfo']['address'] = value
                        elif 'loại hình' in label or 'type' in label:
                            university_details['basicInfo']['type'] = value
                        elif 'sđt' in label or 'phone' in label:
                            university_details['basicInfo']['phone'] = value
                        elif 'web' in label or 'website' in label:
                            try:
                                link_elem = info_row.find_element(By.TAG_NAME, "a")
                                university_details['basicInfo']['website'] = link_elem.get_attribute('href')
                            except:
                                university_details['basicInfo']['website'] = value
                    except:
                        continue
                        
            except Exception as e:
                print(f"    Không lấy được thông tin cơ bản: {str(e)[:50]}")
            
            # 2. Lấy bảng điểm chuẩn (tab đầu tiên)
            try:
                # Tìm bảng điểm chuẩn đầu tiên
                tables = detail_section.find_elements(By.TAG_NAME, "table")
                if tables:
                    score_table = tables[0]  # Bảng điểm chuẩn thường là bảng đầu tiên
                    rows = score_table.find_elements(By.TAG_NAME, "tr")[1:]  # Bỏ header
                    
                    for major_row in rows:
                        try:
                            # Kiểm tra xem có phải hàng phân cách không
                            row_class = major_row.get_attribute("class")
                            if row_class and "DetailUniversity-o7jUt" in row_class:
                                continue
                                
                            cells = major_row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 3:
                                major_code = cells[0].text.strip()
                                major_name = cells[1].text.strip()
                                
                                # Bỏ qua hàng trống
                                if not major_code or not major_name:
                                    continue
                                
                                # Lấy điểm các năm
                                scores = {}
                                years = ['2025', '2024', '2023', '2022', '2021', '2020']
                                
                                for j, year in enumerate(years):
                                    if j + 2 < len(cells):
                                        score_text = cells[j + 2].text.strip()
                                        if score_text and score_text != '-':
                                            try:
                                                scores[year] = float(score_text)
                                            except ValueError:
                                                scores[year] = score_text
                                
                                university_details['universityMajors'].append({
                                    'code': major_code,
                                    'name': major_name,
                                    'scores': scores
                                })
                        except Exception as e:
                            continue
                            
            except NoSuchElementException:
                pass
            
            # 3. Lấy thông tin tuyển sinh (tab thứ hai)
            try:
                # Click vào tab "Thông tin tuyển sinh"
                tab_buttons = detail_section.find_elements(By.CSS_SELECTOR, ".DetailUniversity-RF4rK p")
                admission_tab = None
                for tab in tab_buttons:
                    if "thông tin tuyển sinh" in tab.text.lower():
                        admission_tab = tab
                        break
                
                if admission_tab:
                    driver.execute_script("arguments[0].click();", admission_tab)
                    time.sleep(1)
                    
                    # Lấy thông tin tuyển sinh
                    admission_section = detail_section.find_element(By.CLASS_NAME, "DetailUniversity-ySIbI")
                    
                    # Lấy tất cả HTML của phần thông tin tuyển sinh
                    university_details['admissionInfo']['method'] = ""
                    university_details['admissionInfo']['profile'] = ""
                    university_details['admissionInfo']['target'] = ""
                    university_details['admissionInfo']['region'] = ""
                    university_details['admissionInfo']['fee'] = ""
                    
                    # Tìm các section theo h4
                    h4_elements = admission_section.find_elements(By.TAG_NAME, "h4")
                    
                    for h4 in h4_elements:
                        try:
                            h4_text = h4.text.strip().lower()
                            # Tìm div content tiếp theo
                            next_div = h4.find_element(By.XPATH, "following-sibling::div[1]")
                            content = next_div.get_attribute('innerHTML') or next_div.text
                            
                            if 'phương thức' in h4_text:
                                university_details['admissionInfo']['method'] = content
                            elif 'hồ sơ' in h4_text:
                                university_details['admissionInfo']['profile'] = content
                            elif 'đối tượng' in h4_text:
                                university_details['admissionInfo']['target'] = content
                            elif 'phạm vi' in h4_text:
                                university_details['admissionInfo']['region'] = content
                            elif 'học phí' in h4_text:
                                university_details['admissionInfo']['fee'] = content
                        except:
                            continue
                            
            except Exception as e:
                print(f"Không lấy được thông tin tuyển sinh: {str(e)[:50]}")
            
            # Đóng chi tiết
            try:
                driver.execute_script("arguments[0].click();", expand_button)
                time.sleep(0.5)
            except:
                pass
            
            return university_details
            
        except TimeoutException:
            print(f"{university_name}: Timeout khi load chi tiết")
            return {'basicInfo': {}, 'admissionInfo': {}, 'universityMajors': []}
            
    except Exception as e:
        print(f"{university_name}: Lỗi {str(e)[:100]}")
        return {'basicInfo': {}, 'admissionInfo': {}, 'universityMajors': []}

def crawl_page_universities(driver, page_num=1):
    """Crawl các trường từ một trang"""
    print(f"\n=== TRANG {page_num} ===")
    
    # Đợi trang load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "TableContentRow-ykl5m"))
        )
    except TimeoutException:
        print(f"Timeout khi load trang {page_num}")
        return []
    
    university_rows = driver.find_elements(By.CLASS_NAME, "TableContentRow-ykl5m")
    print(f"Tìm thấy {len(university_rows)} trường")
    
    universities = []
    
    for i, row in enumerate(university_rows):
        try:
            # Lấy thông tin cơ bản
            name_element = row.find_element(By.CLASS_NAME, "TableContentRow-bXCw0")
            code_element = row.find_element(By.CLASS_NAME, "TableContentRow-wNIUX")
            city_element = row.find_element(By.CLASS_NAME, "TableContentRow-xz8Xi")
            
            university_code = code_element.text.strip()
            university_name = name_element.text.strip()
            city = city_element.text.strip()
            
            print(f"{i+1:2d}. {university_name} ({university_code})", end=" -> ")
            
            # Crawl chi tiết đầy đủ
            details = crawl_university_details(driver, row, university_name)
            
            university_data = {
                'name': university_name,
                'universityCode': university_code,
                'acronym': details['basicInfo'].get('acronym', ''),
                'address': details['basicInfo'].get('address', ''),
                'type': details['basicInfo'].get('type', ''),
                'phone': details['basicInfo'].get('phone', ''),
                'website': details['basicInfo'].get('website', ''),
                'city': [city],
                'universityMajors': details['universityMajors'],
                'method': details['admissionInfo'].get('method', ''),
                'profile': details['admissionInfo'].get('profile', ''),
                'target': details['admissionInfo'].get('target', ''),
                'region': details['admissionInfo'].get('region', ''),
                'fee': details['admissionInfo'].get('fee', '')
            }
            
            universities.append(university_data)
            print(f"{len(details['universityMajors'])} ngành")
            
        except Exception as e:
            print(f"{i+1:2d}. Lỗi: {str(e)[:50]}")
            continue
    
    return universities

def go_to_next_page(driver, target_page):
    """Chuyển đến trang tiếp theo"""
    try:
        # Tìm các nút số trang
        page_links = driver.find_elements(By.XPATH, f"//a[text()='{target_page}'] | //button[text()='{target_page}'] | //*[text()='{target_page}' and (@onclick or @href)]")
        
        for link in page_links:
            try:
                if link.is_displayed() and link.is_enabled():
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(3)
                    return True
            except:
                continue
        
        # Nếu không tìm thấy số trang, thử tìm nút "next"
        next_buttons = driver.find_elements(By.XPATH, "//*[contains(@class, 'next') or contains(text(), 'next') or contains(text(), 'Next') or contains(text(), '→')]")
        
        for btn in next_buttons:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
                    return True
            except:
                continue
                
        return False
        
    except Exception as e:
        print(f"Lỗi khi chuyển trang: {e}")
        return False

def crawl_all_pages():
    """Crawl tất cả các trang"""
    driver = setup_driver()
    
    try:
        all_universities = []
        
        # Trang đầu tiên
        print("Đang truy cập trang web...")
        driver.get("https://hoctap.coccoc.com/tim-truong-dh-cd")
        
        # Crawl trang đầu tiên
        universities = crawl_page_universities(driver, 1)
        all_universities.extend(universities)
        
        # Crawl các trang tiếp theo
        for page_num in range(2, 13):  # Trang 2 đến 12
            print(f"\nChuyển đến trang {page_num}...")
            
            if go_to_next_page(driver, page_num):
                universities = crawl_page_universities(driver, page_num)
                if universities:
                    all_universities.extend(universities)
                else:
                    print(f"Trang {page_num} trống, dừng crawl")
                    break
            else:
                print(f"Không thể chuyển đến trang {page_num}, dừng crawl")
                break
        
        return all_universities
        
    finally:
        driver.quit()

if __name__ == "__main__":    
    # Tạo thư mục data nếu chưa có
    os.makedirs("data", exist_ok=True)
    
    start_time = time.time()
    
    # Crawl dữ liệu
    universities = crawl_all_pages()
    
    end_time = time.time()
    
    if universities:
        print(f"\nCrawled {len(universities)} trường")
        print(f"Thời gian: {end_time - start_time:.1f} giây")
        
        # Lưu kết quả
        with open("data/uni_data.json", 'w', encoding='utf-8') as f:
            json.dump(universities, f, ensure_ascii=False, indent=2)
        
        print("Dữ liệu đã được lưu vào data/uni_data.json")
        
    else:
        print("KHÔNG CRAWL ĐƯỢC DỮ LIỆU NÀO!")
