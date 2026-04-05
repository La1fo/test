"""Canonical constants for add-location flow."""

INTEGRATION_ENABLED = True
MAX_TAGS = 5
MAX_PHOTOS = 8
MAX_PHOTO_SIZE_MB = 10
MAX_PHOTO_SIZE_BYTES = MAX_PHOTO_SIZE_MB * 1024 * 1024
ALLOWED_PHOTO_MIME = ["image/jpeg", "image/png", "image/webp"]

BOT_TAG_CATALOG = {
    "Еда": ["кафе", "ресторан", "бар", "фастфуд", "пекарня"],
    "Отдых": ["парк", "лес", "озеро", "река", "пляж", "смотровая площадка", "место для прогулки"],
    "Город": ["магазин", "рынок", "торговый центр", "спортзал", "коворкинг", "библиотека", "учебное место"],
    "Культура": ["историческое место", "памятник", "музей", "архитектура", "церковь", "заброшенное", "культурное место"],
    "Развлечения": ["кино", "клуб", "концертная площадка", "арт-пространство", "игровое место", "мероприятие", "ночное место"],
    "Атмосфера": ["тихое", "уютное", "популярное", "скрытое", "туристическое", "фотогеничное"],
    "Активности": ["прогулка", "пикник", "работа", "свидание", "спорт", "фотосъёмка", "отдых"],
    "Доступность": ["бесплатно", "платно", "круглосуточно", "семейное место", "подходит для детей", "можно с животными"],
}

TAG_CATALOG = [
    {"id": "cafe", "label": "кафе", "category": "Еда"},
    {"id": "restaurant", "label": "ресторан", "category": "Еда"},
    {"id": "bar", "label": "бар", "category": "Еда"},
    {"id": "fastfood", "label": "фастфуд", "category": "Еда"},
    {"id": "bakery", "label": "пекарня", "category": "Еда"},
    {"id": "park", "label": "парк", "category": "Отдых"},
    {"id": "forest", "label": "лес", "category": "Отдых"},
    {"id": "lake", "label": "озеро", "category": "Отдых"},
    {"id": "river", "label": "река", "category": "Отдых"},
    {"id": "beach", "label": "пляж", "category": "Отдых"},
    {"id": "viewpoint", "label": "смотровая площадка", "category": "Отдых"},
    {"id": "walk_place", "label": "место для прогулки", "category": "Отдых"},
    {"id": "shop", "label": "магазин", "category": "Город"},
    {"id": "market", "label": "рынок", "category": "Город"},
    {"id": "mall", "label": "торговый центр", "category": "Город"},
    {"id": "gym", "label": "спортзал", "category": "Город"},
    {"id": "coworking", "label": "коворкинг", "category": "Город"},
    {"id": "library", "label": "библиотека", "category": "Город"},
    {"id": "study_place", "label": "учебное место", "category": "Город"},
    {"id": "historical", "label": "историческое место", "category": "Культура"},
    {"id": "monument", "label": "памятник", "category": "Культура"},
    {"id": "museum", "label": "музей", "category": "Культура"},
    {"id": "architecture", "label": "архитектура", "category": "Культура"},
    {"id": "church", "label": "церковь", "category": "Культура"},
    {"id": "abandoned", "label": "заброшенное", "category": "Культура"},
    {"id": "cultural_place", "label": "культурное место", "category": "Культура"},
    {"id": "cinema", "label": "кино", "category": "Развлечения"},
    {"id": "club", "label": "клуб", "category": "Развлечения"},
    {"id": "concert", "label": "концертная площадка", "category": "Развлечения"},
    {"id": "art_space", "label": "арт-пространство", "category": "Развлечения"},
    {"id": "game_place", "label": "игровое место", "category": "Развлечения"},
    {"id": "event", "label": "мероприятие", "category": "Развлечения"},
    {"id": "night_place", "label": "ночное место", "category": "Развлечения"},
    {"id": "quiet", "label": "тихое", "category": "Атмосфера"},
    {"id": "cozy", "label": "уютное", "category": "Атмосфера"},
    {"id": "popular", "label": "популярное", "category": "Атмосфера"},
    {"id": "hidden", "label": "скрытое", "category": "Атмосфера"},
    {"id": "touristic", "label": "туристическое", "category": "Атмосфера"},
    {"id": "photogenic", "label": "фотогеничное", "category": "Атмосфера"},
    {"id": "walk", "label": "прогулка", "category": "Активности"},
    {"id": "picnic", "label": "пикник", "category": "Активности"},
    {"id": "work", "label": "работа", "category": "Активности"},
    {"id": "date", "label": "свидание", "category": "Активности"},
    {"id": "sport", "label": "спорт", "category": "Активности"},
    {"id": "photo_shoot", "label": "фотосъёмка", "category": "Активности"},
    {"id": "rest", "label": "отдых", "category": "Активности"},
    {"id": "free", "label": "бесплатно", "category": "Доступность"},
    {"id": "paid", "label": "платно", "category": "Доступность"},
    {"id": "open_24_7", "label": "круглосуточно", "category": "Доступность"},
    {"id": "family", "label": "семейное место", "category": "Доступность"},
    {"id": "kids", "label": "подходит для детей", "category": "Доступность"},
    {"id": "pets", "label": "можно с животными", "category": "Доступность"},
]

SUBMIT_DISABLED_MESSAGE = "Проверьте данные и отправьте локацию на модерацию."
PREVIEW_WARNING = "После отправки локация будет создана со статусом pending и уйдёт на модерацию."
