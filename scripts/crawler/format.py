from typing import TypedDict, Dict, Literal, get_args

TITLES = Literal[
    "Id", 
    "Tên trường", 
    "Loại hình cơ sở đào tạo", 
    "Loại trường", 
    "Cơ quan quản lý trực tiếp",
    "Ký hiệu",
    "Tên tiếng Anh",
    "Website",
    "Tỉnh, thành phố",
    "Được kiểm định bởi tổ chức kiểm định chất lượng giáo dục",
    "Ngày cấp giấy chứng nhận kiểm định chất lượng",
    "Ngày hết hạn giá trị của giấy chứng nhận kiểm định chất lượng"
]

GeneralInfo = Dict[TITLES, str]