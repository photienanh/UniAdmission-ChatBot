import pickle 
try:
    from format import GeneralInfo
except:
    from ..format import GeneralInfo
    
def get_uni_info() -> list[GeneralInfo]:
    data: list[GeneralInfo] = []
    with open('data/info/info.pkl', 'rb') as file:
        data = pickle.load(file)
    uni_data: list[GeneralInfo] = [] # Lọc các trường, chỉ lấy đại học và học viện
    for item in data:
        if item['Loại hình cơ sở đào tạo'] in ("Trường đại học", "Đại học","Học viện"):
            uni_data.append(item)
        else:
            # print(item['Loại hình cơ sở đào tạo']) 
            pass
    return uni_data