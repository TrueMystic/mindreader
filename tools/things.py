"""База предметов для игры «Угадаю, кого ты загадал» (составлена вручную).
Строка: Русское название | Английская статья Википедии (для фото) | признаки через пробел.
Признаки:
 E электрическое/на батарейках  S экран  B кнопки  MV мотор/движущиеся части
 K кухня  T ванная  L спальня  O офис/школа  G улица/сад/дача
 C готовит/греет еду  U из этого едят/пьют  W пишут/рисуют  CN уборка  CM связь  TM время/измерение
 MN деньги/оплата  MD здоровье/лекарства  TL инструмент для ремонта  SP спорт  TY игрушка/игра  MU музыка
 CL одежда  H носят на голове  FT обувь  J украшение/аксессуар  F мебель  V транспорт  WH колёса
 SH острое  HT нагревается  CO холод  WA связано с водой/жидкостью  CT в нём что-то хранят/носят  LT светит  SN издаёт звук
 P помещается в карман  BIG больше человека  HV не поднять одному
 ME металл  WO дерево  PL пластик  GL стекло  FA ткань/мягкое  PA бумага
 D пользуются каждый день  EV есть почти в каждом доме  CH в основном для детей  OLD существовало 100+ лет назад  LX дорогая роскошь
"""
import json, os

RAW = """
Телефон|Smartphone|E S B CM P D EV PL GL SN LT TM
Ноутбук|Laptop|E S B O CM PL ME D EV
Компьютер|Desktop computer|E S B O CM PL ME EV
Телевизор|Television set|E S B L SN LT PL GL EV D
Планшет|Tablet computer|E S CM PL GL EV
Наушники|Headphones|E MU SN P PL D
Часы|Watch|E TM J P ME GL D OLD
Будильник|Alarm clock|E B L TM SN PL EV OLD
Настенные часы|Clock|TM WO GL ME EV OLD SN
Фотоаппарат|Camera|E B S PL ME GL OLD
Пульт|Remote control|E B L PL P EV D
Зарядка|Battery charger|E P PL EV D
Колонка|Loudspeaker|E MU SN PL EV
Микрофон|Microphone|E MU SN ME P
Игровая приставка|Video game console|E B TY S PL
Джойстик|Gamepad|E B TY PL P
Принтер|Printer (computing)|E B O PA PL MV
Клавиатура|Computer keyboard|E B O PL D EV
Компьютерная мышь|Computer mouse|E B O PL P D EV
Флешка|USB flash drive|E O P PL ME
Батарейка|Battery (electricity)|E P ME EV
Лампочка|Incandescent light bulb|E LT HT GL EV OLD
Настольная лампа|Lamp|E LT O L ME PL EV
Фонарик|Flashlight|E LT P ME PL EV
Свеча|Candle|LT HT EV OLD
Люстра|Chandelier|E LT GL ME BIG OLD
Холодильник|Refrigerator|E K CO CT BIG HV ME EV D
Морозильник|Freezer|E K CO CT BIG HV ME
Микроволновка|Microwave oven|E B K C HT CT ME GL EV D SN
Плита|Kitchen stove|E K C HT ME HV EV D OLD
Духовка|Oven|E K C HT CT ME GL HV EV OLD
Чайник|Kettle|E K C HT WA ME PL EV D SN
Тостер|Toaster|E K C HT ME EV SN
Кофемашина|Coffeemaker|E B K C HT WA ME PL D
Блендер|Blender|E B K MV PL GL SH SN
Миксер|Mixer (appliance)|E B K MV ME SN
Мультиварка|Multicooker|E B K C HT CT PL ME
Посудомоечная машина|Dishwasher|E B K CN WA MV BIG HV ME
Стиральная машина|Washing machine|E B T CN WA MV HV ME EV D SN
Пылесос|Vacuum cleaner|E CN MV WH PL EV SN
Утюг|Clothes iron|E HT CN ME PL EV OLD
Фен|Hair dryer|E T HT MV PL EV SN D
Электробритва|Electric shaver|E T MV PL ME SN P
Зубная щётка|Toothbrush|T PL D EV P
Кондиционер|Air conditioning|E CO MV PL BIG SN
Вентилятор|Mechanical fan|E MV PL ME SN EV
Обогреватель|Space heater|E HT ME
Батарея отопления|Radiator (heating)|HT ME WA HV EV OLD
Робот-пылесос|Robotic vacuum cleaner|E CN MV WH PL
Электросамокат|Electric kick scooter|E V WH MV ME
Кастрюля|Cooking pot|K C HT ME CT WA EV D OLD
Сковородка|Frying pan|K C HT ME EV D OLD
Тарелка|Plate (dishware)|K U EV D OLD GL
Чашка|Cup|K U WA CT EV D OLD GL
Кружка|Mug|K U WA CT EV D OLD
Стакан|Drinking glass|K U WA GL CT EV D OLD
Бокал|Wine glass|K U WA GL OLD
Ложка|Spoon|K U ME P EV D OLD
Вилка|Fork|K U ME SH EV D OLD
Нож|Knife|K SH ME EV D OLD TL
Палочки для еды|Chopsticks|K U WO P OLD
Половник|Ladle (spoon)|K ME EV OLD
Разделочная доска|Cutting board|K WO EV D OLD
Тёрка|Grater|K SH ME EV OLD
Скалка|Rolling pin|K WO EV OLD
Термос|Vacuum flask|K WA CT HT ME PL
Бутылка|Bottle|WA CT GL PL EV D OLD
Банка|Jar|K CT GL EV OLD
Поднос|Tray|K ME PL WO OLD
Открывашка|Bottle opener|K ME P OLD
Солонка|Salt shaker|K CT GL EV OLD P
Самовар|Samovar|K HT WA ME OLD CT
Мусорное ведро|Waste container|K CN CT PL EV D
Ведро|Bucket|CN WA CT PL ME OLD
Губка|Sponge (tool)|K CN WA FA P EV D
Веник|Broom|CN WO EV OLD
Швабра|Mop|CN WA WO PL EV OLD
Совок|Dustpan|CN PL EV
Тряпка|Rag|CN WA FA EV OLD
Мыло|Soap|T CN WA P EV D OLD
Шампунь|Shampoo|T WA CT PL EV D
Полотенце|Towel|T WA FA EV D OLD
Зеркало|Mirror|T GL EV D OLD
Расчёска|Comb|T PL P EV D OLD
Ванна|Bathtub|T WA BIG HV EV OLD
Унитаз|Toilet|T WA HV EV D OLD
Душ|Shower|T WA ME EV D
Кран|Tap (valve)|K T WA ME EV D
Раковина|Sink|K T WA EV D
Туалетная бумага|Toilet paper|T PA EV D
Бритва|Razor|T SH ME P EV OLD
Зубная паста|Toothpaste|T CT P EV D
Кровать|Bed|L F WO FA BIG HV EV D OLD
Подушка|Pillow|L FA EV D OLD
Одеяло|Duvet|L FA EV D OLD
Матрас|Mattress|L FA BIG EV D
Шкаф|Wardrobe|L F CT WO BIG HV EV OLD
Диван|Couch|F FA BIG HV EV D OLD
Кресло|Chair|F FA EV OLD
Стул|Chair|F WO EV D OLD
Стол|Table (furniture)|F WO EV D OLD
Письменный стол|Desk|F O WO OLD
Табурет|Stool (seat)|F WO EV OLD
Полка|Shelf (storage)|F CT WO EV OLD
Комод|Chest of drawers|F L CT WO HV OLD
Тумбочка|Nightstand|F L CT WO EV
Кресло-качалка|Rocking chair|F WO MV OLD
Гамак|Hammock|G FA L OLD
Ковёр|Carpet|FA EV OLD
Шторы|Curtain|L FA EV OLD
Вешалка|Clothes hanger|CL PL ME EV D
Дверь|Door|WO BIG EV D OLD MV
Окно|Window|GL BIG EV D OLD
Ключ|Key (lock)|ME P D EV OLD
Замок|Lock and key|ME P OLD
Зонт|Umbrella|G WA FA ME MV EV OLD
Очки|Glasses|J GL P D OLD MD
Солнцезащитные очки|Sunglasses|J GL PL P G
Кошелёк|Wallet|MN CT P FA D OLD
Сумка|Handbag|J CT FA D
Рюкзак|Backpack|O CT FA D CH
Чемодан|Suitcase|CT WH PL FA V
Кольцо|Ring (jewellery)|J ME P OLD LX
Цепочка|Necklace|J ME P OLD LX
Серьги|Earring|J ME P OLD
Браслет|Bracelet|J ME P OLD
Корона|Crown (headgear)|H J ME LX OLD
Галстук|Necktie|CL FA OLD
Шапка|Knit cap|CL H FA D
Кепка|Baseball cap|CL H FA D
Шляпа|Hat|CL H FA OLD
Шлем|Helmet|H SP V PL ME
Футболка|T-shirt|CL FA D EV
Джинсы|Jeans|CL FA D EV
Платье|Dress|CL FA OLD
Куртка|Jacket|CL FA D G
Носки|Sock|CL FA D EV OLD
Перчатки|Glove|CL FA G OLD
Шарф|Scarf|CL FA G OLD
Пижама|Pajamas|CL L FA
Купальник|Swimsuit|CL WA FA SP
Кроссовки|Sneakers|CL FT SP D
Тапочки|Slipper|CL FT FA EV D
Сапоги|Boot|CL FT G OLD
Ремень|Belt (clothing)|CL J OLD
Ручка|Pen|O W P PL D EV
Карандаш|Pencil|O W WO P EV OLD CH
Фломастер|Marker pen|O W PL P CH
Мел|Chalk|O W P OLD
Ластик|Eraser|O W P CH
Линейка|Ruler|O TM PL WO
Тетрадь|Exercise book|O W PA CH D
Книга|Book|O PA EV OLD
Газета|Newspaper|PA OLD
Журнал|Magazine|PA OLD
Блокнот|Notebook|O W PA P
Ножницы|Scissors|O SH ME EV OLD
Степлер|Stapler|O ME
Скрепка|Paper clip|O ME P
Клей|Adhesive|O CT CH
Калькулятор|Calculator|E B O S TM PL P
Глобус|Globe|O CH OLD
Доска|Blackboard|O W BIG OLD
Конверт|Envelope|PA CM OLD
Деньги|Banknote|MN PA P D OLD
Монета|Coin|MN ME P OLD
Банковская карта|Payment card|MN PL P D
Копилка|Piggy bank|MN CT CH
Паспорт|Passport|PA P OLD
Градусник|Medical thermometer|MD TM GL P EV
Таблетки|Tablet (pharmacy)|MD P EV
Шприц|Syringe|MD SH PL
Пластырь|Adhesive bandage|MD P EV
Аптечка|First aid kit|MD CT EV
Весы|Weighing scale|TM ME EV
Молоток|Hammer|TL ME WO EV OLD
Отвёртка|Screwdriver|TL ME P EV
Дрель|Drill|E TL MV ME SN
Пила|Saw|TL SH ME OLD
Топор|Axe|TL SH ME WO G OLD
Лопата|Shovel|TL G ME WO OLD
Грабли|Rake (tool)|TL G WO OLD
Гаечный ключ|Wrench|TL ME
Плоскогубцы|Pliers|TL ME
Рулетка|Tape measure|TL TM ME P
Лестница|Ladder|TL ME WO BIG OLD
Гвоздь|Nail (fastener)|TL ME SH P OLD
Верёвка|Rope|TL FA OLD
Изолента|Electrical tape|TL PL P
Лейка|Watering can|G WA CT ME PL
Газонокосилка|Lawn mower|E G MV WH ME SN
Шланг|Garden hose|G WA PL
Мангал|Barbecue grill|G C HT ME
Палатка|Tent|G FA BIG
Тачка|Wheelbarrow|G WH ME
Машина|Car|E V WH MV ME GL BIG HV D SN
Велосипед|Bicycle|V WH SP ME OLD
Самокат|Kick scooter|V WH ME CH
Мотоцикл|Motorcycle|V WH MV ME HV SN
Автобус|Bus|V WH MV BIG HV SN
Поезд|Train|V WH MV ME BIG HV OLD SN
Самолёт|Airplane|V MV ME BIG HV SN
Вертолёт|Helicopter|V MV ME BIG HV SN
Корабль|Ship|V WA MV ME BIG HV OLD
Лодка|Boat|V WA WO BIG OLD
Ракета|Rocket|V MV ME BIG HV
Скейтборд|Skateboard|V WH SP WO CH
Ролики|Inline skates|FT WH SP CH
Коньки|Ice skate|FT SP CO SH ME
Лыжи|Skiing|SP CO G OLD
Санки|Sled|G CO CH WO OLD
Коляска|Baby transport|V WH CH FA
Мяч|Ball|SP TY CH G
Футбольный мяч|Football (ball)|SP TY G
Баскетбольный мяч|Basketball (ball)|SP TY G
Теннисная ракетка|Racket (sports equipment)|SP
Гантели|Dumbbell|SP ME HV
Боксёрские перчатки|Boxing glove|SP CL FA
Скакалка|Skipping rope|SP CH
Удочка|Fishing rod|SP G WA
Шахматы|Chess|TY WO OLD
Карты|Playing card|TY PA P OLD
Кубик Рубика|Rubik's Cube|TY PL CH P
Кукла|Doll|TY CH PL FA OLD
Плюшевый мишка|Teddy bear|TY CH FA L
Конструктор Лего|Lego|TY CH PL
Пазл|Jigsaw puzzle|TY PA CH
Воздушный шарик|Balloon|TY CH PL
Игральные кости|Dice|TY P PL OLD
Юла|Spinning top|TY CH MV OLD
Гитара|Guitar|MU SN WO OLD
Пианино|Piano|MU SN B WO BIG HV OLD
Скрипка|Violin|MU SN WO OLD
Барабан|Drum|MU SN OLD
Труба|Trumpet|MU SN ME OLD
Флейта|Flute|MU SN OLD
Гармошка|Accordion|MU SN B OLD
Свисток|Whistle|SN P ME PL SP
Колокольчик|Bell|SN ME OLD
Картина|Painting|O WO OLD LX
Ваза|Vase|GL CT OLD
Цветочный горшок|Flowerpot|G CT EV
Аквариум|Aquarium|WA GL CT E
Клетка для птиц|Birdcage|CT ME
Ёлка новогодняя|Christmas tree|LT CH
Фоторамка|Picture frame|WO GL EV
Календарь|Calendar|TM PA O
Компас|Compass|TM ME P OLD G
Бинокль|Binoculars|GL ME G OLD
Телескоп|Telescope|GL ME OLD
Микроскоп|Microscope|GL ME O OLD
Песочные часы|Hourglass|TM GL OLD
Спички|Match|HT P EV OLD
Зажигалка|Lighter|HT P ME PL
Сигарета|Cigarette|HT P PA
Кальян|Hookah|HT WA GL OLD
Сейф|Safe|MN CT ME HV
Пакет|Plastic bag|CT PL EV D
Коробка|Box|CT PA EV
Корзина|Basket|CT WO OLD
Мешок|Sack|CT FA OLD
Колесо|Wheel|WH V OLD
Шина|Tire|WH V
Руль|Steering wheel|V
Якорь|Anchor|WA ME HV OLD
Меч|Sword|SH ME OLD
Пистолет|Pistol|ME SN P
Лук и стрелы|Bow and arrow|SP SH WO OLD
Щит|Shield|ME WO OLD
Кольчуга|Mail (armour)|CL ME OLD
Флаг|Flag|FA OLD
Медаль|Medal|SP J ME OLD
Кубок|Trophy|SP ME LX
Подкова|Horseshoe|ME OLD
Свисток судьи|Referee whistle|SN SP P
Светофор|Traffic light|E LT G BIG
Фонарный столб|Street light|E LT G BIG ME
Почтовый ящик|Letter box|CM CT ME G
Скамейка|Bench (furniture)|F G WO
Качели|Swing (seat)|G CH MV TY
Батут|Trampoline|G CH SP TY BIG
Снеговик|Snowman|G CO CH
Пылесос ручной|Handheld vacuum|E CN PL
Бигуди|Hair roller|T J PL
Помада|Lipstick|J P T
Духи|Perfume|J GL P LX
Кисточка|Paintbrush|W O WO
Краски|Paint|W O CT
Мольберт|Easel|W WO
Ящик с инструментами|Toolbox|TL CT ME
"""

def main():
    out = []
    seen = set()
    for line in RAW.strip().splitlines():
        ru, wiki, codes = [x.strip() for x in line.split("|")]
        if ru in seen: continue
        seen.add(ru)
        f = sorted(set(codes.split()))
        s = 40 + (25 if "D" in f else 0) + (20 if "EV" in f else 0)
        out.append({"n": ru, "w": wiki, "f": f, "s": s})
    os.makedirs("data", exist_ok=True)
    with open("data/things.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print(len(out), "things")

if __name__ == "__main__":
    main()
