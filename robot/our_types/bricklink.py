from typing_extensions import TypedDict


class BricklinkPartData(TypedDict):
    no: str
    name: str
    type: str
    category_id: int
    alternate_no: str
    image_url: str
    thumbnail_url: str
    weight: str
    dim_x: str
    dim_y: str
    dim_z: str
    year_released: int
    description: str
    is_obsolete: bool
