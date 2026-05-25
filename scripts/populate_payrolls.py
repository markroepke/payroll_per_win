"""One-shot script to populate data/payrolls_opening_day.csv.

Sources:
  - 2000-2019, 2021-2025: stevetheump.com (compiled from AP / Spotrac / Cot's)
  - 2020:                 thebaseballcube.com (pre-pandemic Opening Day commitments)

The 2020 figures are the originally-committed full-season Opening Day
payrolls, NOT the COVID-prorated cash that was actually paid out for the
60-game season. This keeps 2020 on the same basis as the other seasons.

Historical team names are mapped to a single canonical franchise name so
that, e.g., the 2000 Montreal Expos and the 2025 Washington Nationals are
treated as the same franchise.
"""

from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = REPO_ROOT / "data" / "payrolls_opening_day.csv"
SOURCE_DEFAULT = "stevetheump.com (compiled from AP / Spotrac / Cot's)"
SOURCE_2020 = "thebaseballcube.com (pre-pandemic Opening Day commitments)"

# Map every historical name variant to a single canonical franchise label.
SHORT_TO_FULL = {
    # Yankees
    "NY Yankees": "New York Yankees", "N.Y. Yankees": "New York Yankees",
    "Yankees": "New York Yankees", "New York Yankees": "New York Yankees",
    # Mets
    "NY Mets": "New York Mets", "Mets": "New York Mets",
    "New York Mets": "New York Mets",
    # Dodgers
    "Los Angeles": "Los Angeles Dodgers", "LA Dodgers": "Los Angeles Dodgers",
    "Los Angeles Dodgers": "Los Angeles Dodgers", "Dodgers": "Los Angeles Dodgers",
    # Angels (Anaheim -> LAAofA -> LAA)
    "Anaheim": "Los Angeles Angels", "Anaheim Angels": "Los Angeles Angels",
    "Los Angeles Angels of Anaheim": "Los Angeles Angels",
    "Los Angeles Angels": "Los Angeles Angels", "Angels": "Los Angeles Angels",
    # Red Sox
    "Boston": "Boston Red Sox", "Boston Red Sox": "Boston Red Sox",
    "Red Sox": "Boston Red Sox",
    # Astros
    "Houston": "Houston Astros", "Houston Astros": "Houston Astros",
    "Astros": "Houston Astros",
    # Phillies
    "Philadelphia": "Philadelphia Phillies",
    "Philadelphia Phillies": "Philadelphia Phillies", "Phillies": "Philadelphia Phillies",
    # Padres
    "San Diego": "San Diego Padres", "San Diego Padres": "San Diego Padres",
    "Padres": "San Diego Padres",
    # Cubs
    "Chicago Cubs": "Chicago Cubs", "Cubs": "Chicago Cubs",
    # Cardinals
    "St. Louis": "St. Louis Cardinals", "St Louis Cardinals": "St. Louis Cardinals",
    "St. Louis Cardinals": "St. Louis Cardinals", "Cardinals": "St. Louis Cardinals",
    # Giants
    "San Francisco": "San Francisco Giants", "SF Giants": "San Francisco Giants",
    "San Francisco Giants": "San Francisco Giants", "Giants": "San Francisco Giants",
    # Braves
    "Atlanta": "Atlanta Braves", "Atlanta Braves": "Atlanta Braves",
    "Braves": "Atlanta Braves",
    # Nationals (Expos -> Nationals)
    "Montreal": "Washington Nationals", "Montreal Expos": "Washington Nationals",
    "Washington": "Washington Nationals",
    "Washington Nationals": "Washington Nationals", "Nationals": "Washington Nationals",
    # Diamondbacks
    "Arizona": "Arizona Diamondbacks",
    "Arizona Diamondbacks": "Arizona Diamondbacks", "Diamondbacks": "Arizona Diamondbacks",
    # Rangers
    "Texas": "Texas Rangers", "Texas Rangers": "Texas Rangers", "Rangers": "Texas Rangers",
    # Rockies
    "Colorado": "Colorado Rockies", "Colorado Rockies": "Colorado Rockies",
    "Rockies": "Colorado Rockies",
    # Reds
    "Cincinnati": "Cincinnati Reds", "Cincinnati Reds": "Cincinnati Reds",
    "Reds": "Cincinnati Reds",
    # White Sox
    "Chicago White Sox": "Chicago White Sox", "Ch. White Sox": "Chicago White Sox",
    "White Sox": "Chicago White Sox",
    # Blue Jays
    "Toronto": "Toronto Blue Jays", "Toronto Blue Jays": "Toronto Blue Jays",
    "Blue Jays": "Toronto Blue Jays",
    # Twins
    "Minnesota": "Minnesota Twins", "Minnesota Twins": "Minnesota Twins",
    "Twins": "Minnesota Twins",
    # Mariners
    "Seattle": "Seattle Mariners", "Seattle Mariners": "Seattle Mariners",
    "Mariners": "Seattle Mariners",
    # Tigers
    "Detroit": "Detroit Tigers", "Detroit Tigers": "Detroit Tigers",
    "Tigers": "Detroit Tigers",
    # Brewers
    "Milwaukee": "Milwaukee Brewers", "Milwaukee Brewers": "Milwaukee Brewers",
    "Brewers": "Milwaukee Brewers",
    # Guardians (Indians -> Guardians)
    "Cleveland": "Cleveland Guardians", "Cleveland Indians": "Cleveland Guardians",
    "Cleveland Guardians": "Cleveland Guardians",
    "Indians": "Cleveland Guardians", "Guardians": "Cleveland Guardians",
    # Royals
    "Kansas City": "Kansas City Royals", "KC Royals": "Kansas City Royals",
    "Kansas City Royals": "Kansas City Royals", "Royals": "Kansas City Royals",
    # Athletics
    "Oakland": "Oakland Athletics", "Oakland Athletics": "Oakland Athletics",
    "Oakland A's": "Oakland Athletics", "Athletics": "Oakland Athletics",
    # Rays (Devil Rays -> Rays)
    "Tampa Bay": "Tampa Bay Rays", "Tampa Bay Devil Rays": "Tampa Bay Rays",
    "Tampa Bay Rays": "Tampa Bay Rays", "Rays": "Tampa Bay Rays",
    # Marlins (Florida -> Miami)
    "Florida": "Miami Marlins", "Florida Marlins": "Miami Marlins",
    "Miami Marlins": "Miami Marlins", "Marlins": "Miami Marlins",
    # Pirates
    "Pittsburgh": "Pittsburgh Pirates", "Pittsburgh Pirates": "Pittsburgh Pirates",
    "Pirates": "Pittsburgh Pirates",
    # Orioles
    "Baltimore": "Baltimore Orioles", "Baltimore Orioles": "Baltimore Orioles",
    "Orioles": "Baltimore Orioles",
}


# Raw figures from stevetheump.com and (for 2020) thebaseballcube.com.
# 2018 values were quoted in $M (e.g. "$235.65M"); converted to integer USD.
# 2025 values were quoted in whole millions.
RAW: dict[int, dict[str, int]] = {
    2000: {
        "NY Yankees": 92_538_260, "Los Angeles": 88_124_286, "Atlanta": 84_537_836,
        "Baltimore": 81_447_435, "Arizona": 81_027_833, "NY Mets": 79_509_776,
        "Boston": 77_940_333, "Cleveland": 75_880_871, "Texas": 70_795_921,
        "Tampa Bay": 62_765_129, "St. Louis": 61_453_863, "Colorado": 61_111_190,
        "Chicago Cubs": 60_539_333, "Seattle": 58_915_000, "Detroit": 58_265_167,
        "San Diego": 54_821_000, "San Francisco": 53_737_826, "Anaheim": 51_464_167,
        "Houston": 51_289_111, "Philadelphia": 47_308_000, "Cincinnati": 46_867_200,
        "Toronto": 46_238_333, "Milwaukee": 36_505_333, "Montreal": 34_807_833,
        "Oakland": 31_971_333, "Chicago White Sox": 31_133_500, "Pittsburgh": 28_928_333,
        "Kansas City": 23_433_000, "Florida": 20_072_000, "Minnesota": 16_519_500,
    },
    2001: {
        "NY Yankees": 109_791_893, "Boston": 109_558_908, "Los Angeles": 108_980_952,
        "NY Mets": 93_174_428, "Cleveland": 91_974_979, "Atlanta": 91_851_687,
        "Texas": 88_504_421, "Arizona": 81_206_513, "St. Louis": 77_270_855,
        "Toronto": 75_798_500, "Seattle": 75_652_500, "Baltimore": 72_426_328,
        "Colorado": 71_068_000, "Chicago Cubs": 64_015_833, "San Francisco": 63_332_667,
        "Chicago White Sox": 62_363_000, "Houston": 60_382_667, "Tampa Bay": 54_951_602,
        "Pittsburgh": 52_698_333, "Detroit": 49_831_167, "Anaheim": 46_568_180,
        "Cincinnati": 45_227_882, "Milwaukee": 43_089_333, "Philadelphia": 41_664_167,
        "San Diego": 38_333_117, "Kansas City": 35_643_000, "Florida": 35_504_167,
        "Montreal": 34_774_500, "Oakland": 33_810_750, "Minnesota": 24_350_000,
    },
    2002: {
        "NY Yankees": 125_928_583, "Boston Red Sox": 108_366_060, "Texas Rangers": 105_302_124,
        "Arizona Diamondbacks": 102_820_000, "LA Dodgers": 94_850_952, "NY Mets": 94_633_593,
        "Atlanta Braves": 93_470_367, "Seattle Mariners": 80_282_668,
        "Cleveland Indians": 78_909_448, "SF Giants": 78_299_835,
        "Toronto Blue Jays": 76_864_333, "Chicago Cubs": 75_690_833,
        "St. Louis Cardinals": 74_098_267, "Houston Astros": 63_448_417,
        "Anaheim Angels": 61_721_667, "Baltimore Orioles": 60_493_487,
        "Philadelphia Phillies": 57_955_000, "Chicago White Sox": 57_052_833,
        "Colorado Rockies": 56_851_043, "Detroit Tigers": 55_048_000,
        "Milwaukee Brewers": 50_287_833, "Kansas City Royals": 47_257_000,
        "Cincinnati Reds": 45_050_390, "Pittsburgh Pirates": 42_323_598,
        "Florida Marlins": 41_979_917, "San Diego Padres": 41_425_000,
        "Minnesota Twins": 40_225_000, "Oakland Athletics": 39_679_746,
        "Montreal Expos": 38_670_500, "Tampa Bay Devil Rays": 34_380_000,
    },
    2003: {
        "NY Yankees": 152_749_814, "NY Mets": 117_176_429, "Atlanta Braves": 106_243_667,
        "LA Dodgers": 105_872_620, "Texas Rangers": 103_491_667, "Boston Red Sox": 99_946_500,
        "Seattle Mariners": 86_959_167, "St Louis Cardinals": 83_486_666,
        "SF Giants": 82_852_167, "Arizona Diamondbacks": 80_640_333,
        "Chicago Cubs": 79_868_333, "Anaheim Angels": 79_031_667,
        "Baltimore Orioles": 73_877_500, "Houston Astros": 71_040_000,
        "Philadelphia Phillies": 70_780_000, "Colorado Rockies": 67_179_667,
        "Cincinnati Reds": 59_355_667, "Minnesota Twins": 55_505_000,
        "Pittsburgh Pirates": 54_812_429, "Montreal Expos": 51_948_500,
        "Toronto Blue Jays": 51_269_000, "Chicago White Sox": 51_010_000,
        "Oakland Athletics": 50_260_834, "Detroit Tigers": 49_168_000,
        "Florida Marlins": 49_050_000, "Cleveland Indians": 48_584_834,
        "San Diego Padres": 47_928_000, "Milwaukee Brewers": 40_627_000,
        "KC Royals": 40_518_000, "Tampa Bay Devil Rays": 19_630_000,
    },
    2004: {
        "N.Y. Yankees": 182_835_513, "Boston": 125_208_542, "Anaheim": 101_084_667,
        "New York Mets": 100_629_303, "Philadelphia": 93_219_167, "Chicago Cubs": 91_101_667,
        "Los Angeles": 89_694_342, "Atlanta": 88_507_788, "San Francisco": 82_019_167,
        "Seattle": 81_543_833, "St. Louis": 75_633_517, "Houston": 74_666_303,
        "Arizona": 70_204_984, "Ch. White Sox": 65_212_500, "Colorado": 64_590_403,
        "Oakland": 59_825_167, "Texas": 54_825_973, "San Diego": 54_639_503,
        "Minnesota": 53_585_000, "Baltimore": 51_212_653, "Toronto": 50_017_000,
        "Kansas City": 47_609_000, "Detroit": 46_353_554, "Montreal": 43_197_500,
        "Cincinnati": 43_067_858, "Florida": 42_118_042, "Cleveland": 34_569_300,
        "Pittsburgh": 32_227_929, "Tampa Bay": 29_506_667, "Milwaukee": 27_518_500,
    },
    2005: {
        "New York Yankees": 205_938_439, "Boston Red Sox": 121_311_945,
        "New York Mets": 104_770_139, "Philadelphia Phillies": 95_337_908,
        "Los Angeles Angels": 95_017_822, "St. Louis Cardinals": 93_319_842,
        "San Francisco Giants": 89_487_842, "Chicago Cubs": 87_210_933,
        "Seattle Mariners": 85_883_333, "Atlanta Braves": 85_148_582,
        "Los Angeles Dodgers": 81_029_500, "Houston Astros": 76_779_022,
        "Chicago White Sox": 75_228_000, "Baltimore Orioles": 74_570_539,
        "Detroit Tigers": 68_998_183, "Arizona Diamondbacks": 63_015_834,
        "San Diego Padres": 62_888_192, "Florida Marlins": 60_375_961,
        "Cincinnati Reds": 59_658_275, "Minnesota Twins": 56_615_000,
        "Oakland Athletics": 55_869_262, "Texas Rangers": 55_307_258,
        "Washington Nationals": 48_581_500, "Colorado Rockies": 47_789_000,
        "Toronto Blue Jays": 45_336_500, "Cleveland Indians": 41_830_400,
        "Milwaukee Brewers": 40_234_833, "Pittsburgh Pirates": 38_138_000,
        "Kansas City Royals": 36_881_000, "Tampa Bay Devil Rays": 29_893_567,
    },
    2006: {
        "New York Yankees": 194_663_079, "Boston Red Sox": 120_099_824,
        "Los Angeles Angels": 103_472_000, "Chicago White Sox": 102_750_667,
        "New York Mets": 101_084_963, "Los Angeles Dodgers": 98_447_187,
        "Chicago Cubs": 94_424_499, "Houston Astros": 92_551_503,
        "Atlanta Braves": 90_156_876, "San Francisco Giants": 90_056_419,
        "St. Louis Cardinals": 88_891_371, "Philadelphia Phillies": 88_273_333,
        "Seattle Mariners": 87_959_833, "Detroit Tigers": 82_612_866,
        "Baltimore Orioles": 72_585_582, "Toronto Blue Jays": 71_915_000,
        "San Diego Padres": 69_896_141, "Texas Rangers": 68_228_662,
        "Minnesota Twins": 63_396_006, "Washington Nationals": 63_143_000,
        "Oakland Athletics": 62_243_079, "Cincinnati Reds": 60_909_519,
        "Arizona Diamondbacks": 59_684_226, "Milwaukee Brewers": 57_568_333,
        "Cleveland Indians": 56_031_500, "Kansas City Royals": 47_294_000,
        "Pittsburgh Pirates": 46_717_750, "Colorado Rockies": 41_233_000,
        "Tampa Bay Devil Rays": 35_417_967, "Florida Marlins": 14_998_500,
    },
    2007: {
        "New York Yankees": 189_639_045, "Boston Red Sox": 143_026_214,
        "New York Mets": 115_231_663, "Los Angeles Angels": 109_251_333,
        "Chicago White Sox": 108_671_833, "Los Angeles Dodgers": 108_454_524,
        "Seattle Mariners": 106_460_833, "Chicago Cubs": 99_670_332,
        "Detroit Tigers": 95_180_369, "Baltimore Orioles": 93_554_808,
        "St. Louis Cardinals": 90_286_823, "San Francisco Giants": 90_219_056,
        "Philadelphia Phillies": 89_428_213, "Houston Astros": 87_759_000,
        "Atlanta Braves": 87_290_833, "Toronto Blue Jays": 81_942_800,
        "Oakland Athletics": 79_366_940, "Minnesota Twins": 71_439_500,
        "Milwaukee Brewers": 70_986_500, "Cincinnati Reds": 68_904_980,
        "Texas Rangers": 68_318_675, "Kansas City Royals": 67_116_500,
        "Cleveland Indians": 61_673_267, "San Diego Padres": 58_110_567,
        "Colorado Rockies": 54_424_000, "Arizona Diamondbacks": 52_067_546,
        "Pittsburgh Pirates": 38_537_833, "Washington Nationals": 37_347_500,
        "Florida Marlins": 30_507_000, "Tampa Bay Devil Rays": 24_123_500,
    },
    2008: {
        "New York Yankees": 209_081_577, "New York Mets": 137_793_376,
        "Detroit Tigers": 137_685_196, "Boston Red Sox": 133_390_035,
        "Chicago White Sox": 121_189_332, "Los Angeles Angels": 119_216_333,
        "Los Angeles Dodgers": 118_588_536, "Chicago Cubs": 118_345_833,
        "Seattle Mariners": 117_666_482, "Atlanta Braves": 102_365_683,
        "St. Louis Cardinals": 99_624_449, "Philadelphia Phillies": 98_269_880,
        "Toronto Blue Jays": 97_793_900, "Houston Astros": 88_930_414,
        "Milwaukee Brewers": 80_937_499, "Cleveland Indians": 78_970_066,
        "San Francisco Giants": 76_594_500, "Cincinnati Reds": 74_117_695,
        "San Diego Padres": 73_677_616, "Colorado Rockies": 68_655_500,
        "Texas Rangers": 67_712_326, "Baltimore Orioles": 67_196_246,
        "Arizona Diamondbacks": 66_202_712, "Kansas City Royals": 58_245_500,
        "Minnesota Twins": 56_932_766, "Washington Nationals": 54_961_000,
        "Pittsburgh Pirates": 48_689_783, "Oakland Athletics": 47_967_126,
        "Tampa Bay Rays": 43_820_597, "Florida Marlins": 21_811_500,
    },
    2009: {
        "N.Y. Yankees": 201_449_289, "New York Mets": 135_773_988,
        "Chicago Cubs": 135_050_000, "Boston": 122_696_000, "Detroit": 115_085_145,
        "Los Angeles Angels": 113_709_000, "Philadelphia": 113_004_048,
        "Houston": 102_996_415, "Los Angeles Dodgers": 100_458_101,
        "Seattle": 98_904_167, "Atlanta": 96_726_167, "Chicago White Sox": 96_068_500,
        "St. Louis": 88_528_411, "San Francisco": 82_161_450, "Cleveland": 81_625_567,
        "Toronto": 80_993_657, "Milwaukee": 80_257_502, "Colorado": 75_201_000,
        "Arizona": 73_571_667, "Cincinnati": 70_968_500, "Kansas City": 70_908_333,
        "Texas": 68_646_023, "Baltimore": 67_101_667, "Minnesota": 65_299_267,
        "Tampa Bay": 63_313_035, "Oakland": 62_310_000, "Washington": 59_328_000,
        "Pittsburgh": 48_743_000, "San Diego": 42_796_700, "Florida": 36_814_000,
    },
    2010: {
        "New York Yankees": 206_333_389, "Boston Red Sox": 162_747_333,
        "Chicago Cubs": 146_859_000, "Philadelphia Phillies": 141_927_381,
        "New York Mets": 132_701_445, "Detroit Tigers": 122_864_929,
        "Chicago White Sox": 108_273_197, "Los Angeles Angels": 105_013_667,
        "Seattle Mariners": 98_376_667, "San Francisco Giants": 97_828_833,
        "Minnesota Twins": 97_559_167, "Los Angeles Dodgers": 94_945_517,
        "St. Louis Cardinals": 93_540_753, "Houston Astros": 92_355_500,
        "Atlanta Braves": 84_423_667, "Colorado Rockies": 84_227_000,
        "Baltimore Orioles": 81_612_500, "Milwaukee Brewers": 81_108_279,
        "Cincinnati Reds": 72_386_544, "Kansas City Royals": 72_267_710,
        "Tampa Bay Rays": 71_923_471, "Toronto Blue Jays": 62_689_357,
        "Washington Nationals": 61_425_000, "Cleveland Indians": 61_203_967,
        "Arizona Diamondbacks": 60_718_167, "Florida Marlins": 55_641_500,
        "Texas Rangers": 55_250_545, "Oakland Athletics": 51_654_900,
        "San Diego Padres": 37_799_300, "Pittsburgh Pirates": 34_943_000,
    },
    2011: {
        "N.Y. Yankees": 201_689_030, "Philadelphia": 172_976_381, "Boston": 161_407_476,
        "Los Angeles Angels": 138_998_524, "Chicago White Sox": 129_285_539,
        "Chicago Cubs": 125_480_664, "New York Mets": 120_147_310,
        "San Francisco": 118_216_333, "Minnesota": 112_737_000, "Detroit": 105_705_232,
        "St. Louis": 105_433_572, "Los Angeles Dodgers": 103_788_990, "Texas": 92_299_265,
        "Colorado": 87_998_071, "Atlanta": 87_003_192, "Seattle": 86_424_600,
        "Milwaukee": 85_497_333, "Baltimore": 85_304_038, "Cincinnati": 76_181_365,
        "Houston": 70_694_000, "Oakland": 66_536_500, "Washington": 63_681_929,
        "Toronto": 62_517_800, "Florida": 56_944_000, "Arizona": 53_639_833,
        "Cleveland": 49_188_867, "Pittsburgh": 46_047_000, "San Diego": 45_869_140,
        "Tampa Bay": 41_932_171, "Kansas City": 36_126_400,
    },
    2012: {
        "New York Yankees": 197_962_289, "Philadelphia Phillies": 174_538_938,
        "Boston Red Sox": 173_186_617, "Los Angeles Angels": 154_485_166,
        "Detroit Tigers": 132_300_000, "Texas Rangers": 120_510_974,
        "Miami Marlins": 118_078_000, "San Francisco Giants": 117_620_683,
        "St. Louis Cardinals": 110_300_862, "Milwaukee Brewers": 97_653_944,
        "Chicago White Sox": 96_919_500, "Los Angeles Dodgers": 95_143_575,
        "Minnesota Twins": 94_085_000, "New York Mets": 93_353_983,
        "Chicago Cubs": 88_197_033, "Atlanta Braves": 83_309_942,
        "Cincinnati Reds": 82_203_616, "Seattle Mariners": 81_978_100,
        "Baltimore Orioles": 81_428_999, "Washington Nationals": 81_336_143,
        "Cleveland Indians": 78_430_300, "Colorado Rockies": 78_069_571,
        "Toronto Blue Jays": 75_489_200, "Arizona Diamondbacks": 74_284_833,
        "Tampa Bay Rays": 64_173_500, "Pittsburgh Pirates": 63_431_999,
        "Kansas City Royals": 60_916_225, "Houston Astros": 60_651_000,
        "Oakland Athletics": 55_372_500, "San Diego Padres": 55_244_700,
    },
    2013: {
        "New York Yankees": 228_835_490, "Los Angeles Dodgers": 216_597_577,
        "Philadelphia Phillies": 165_385_714, "Boston Red Sox": 150_655_500,
        "Detroit Tigers": 148_414_500, "San Francisco Giants": 140_264_334,
        "Los Angeles Angels": 127_896_250, "Chicago White Sox": 119_073_277,
        "Toronto Blue Jays": 117_527_800, "St. Louis Cardinals": 115_222_086,
        "Texas Rangers": 114_090_100, "Washington Nationals": 114_056_769,
        "Cincinnati Reds": 107_491_305, "Chicago Cubs": 104_304_676,
        "Baltimore Orioles": 90_993_333, "Atlanta Braves": 89_778_192,
        "Arizona Diamondbacks": 89_100_500, "Milwaukee Brewers": 82_976_944,
        "Kansas City Royals": 81_491_725, "Pittsburgh Pirates": 79_555_000,
        "Cleveland Indians": 77_772_800, "Minnesota Twins": 75_802_500,
        "New York Mets": 73_396_649, "Seattle Mariners": 72_031_143,
        "Colorado Rockies": 71_924_071, "San Diego Padres": 67_143_600,
        "Oakland Athletics": 60_664_500, "Tampa Bay Rays": 57_895_272,
        "Miami Marlins": 36_341_900, "Houston Astros": 22_062_600,
    },
    2014: {
        "Los Angeles Dodgers": 235_295_219, "New York Yankees": 203_812_506,
        "Philadelphia Phillies": 180_052_723, "Boston Red Sox": 162_817_411,
        "Detroit Tigers": 162_228_527, "Los Angeles Angels": 155_692_000,
        "San Francisco Giants": 154_185_878, "Texas Rangers": 136_036_172,
        "Washington Nationals": 134_704_437, "Toronto Blue Jays": 132_628_700,
        "Arizona Diamondbacks": 112_688_666, "Cincinnati Reds": 112_390_772,
        "St. Louis Cardinals": 111_020_360, "Atlanta Braves": 110_897_341,
        "Baltimore Orioles": 107_406_623, "Milwaukee Brewers": 103_844_806,
        "Colorado Rockies": 95_832_071, "Seattle Mariners": 92_081_943,
        "Kansas City Royals": 92_034_345, "Chicago White Sox": 91_159_254,
        "San Diego Padres": 90_094_196, "New York Mets": 89_051_758,
        "Chicago Cubs": 89_007_857, "Minnesota Twins": 85_776_500,
        "Oakland Athletics": 83_401_400, "Cleveland Indians": 82_534_800,
        "Pittsburgh Pirates": 78_111_667, "Tampa Bay Rays": 77_062_891,
        "Miami Marlins": 47_565_400, "Houston Astros": 44_544_174,
    },
    2015: {
        "Los Angeles Dodgers": 272_789_040, "New York Yankees": 219_282_196,
        "Boston Red Sox": 187_407_202, "Detroit Tigers": 173_813_750,
        "San Francisco Giants": 172_672_111, "Washington Nationals": 164_920_505,
        "Los Angeles Angels": 150_933_083, "Texas Rangers": 142_140_873,
        "Philadelphia Phillies": 135_827_500, "Toronto Blue Jays": 122_506_600,
        "St. Louis Cardinals": 120_869_458, "Seattle Mariners": 119_798_060,
        "Chicago Cubs": 119_006_885, "Cincinnati Reds": 117_197_072,
        "Chicago White Sox": 115_238_678, "Kansas City Royals": 113_618_650,
        "Baltimore Orioles": 110_146_097, "Minnesota Twins": 108_945_000,
        "Milwaukee Brewers": 105_002_536, "Colorado Rockies": 102_006_130,
        "New York Mets": 101_409_244, "San Diego Padres": 100_675_896,
        "Atlanta Braves": 97_578_565, "Arizona Diamondbacks": 91_518_833,
        "Pittsburgh Pirates": 88_278_500, "Cleveland Indians": 86_091_175,
        "Oakland A's": 86_086_667, "Tampa Bay Rays": 76_061_707,
        "Houston Astros": 70_910_100, "Miami Marlins": 68_479_000,
    },
    2016: {
        "Dodgers": 223_352_402, "Yankees": 213_472_857, "Red Sox": 182_161_414,
        "Tigers": 172_282_250, "Giants": 166_495_942, "Nationals": 166_010_977,
        "Angels": 146_449_583, "Rangers": 144_307_373, "Phillies": 133_048_000,
        "Blue Jays": 126_369_628, "Mariners": 122_706_842, "Cardinals": 120_301_957,
        "Reds": 116_732_284, "Cubs": 116_654_522, "Orioles": 115_587_632,
        "Royals": 112_914_525, "Padres": 112_895_700, "Twins": 108_262_000,
        "Mets": 99_626_453, "White Sox": 98_712_867, "Brewers": 98_683_035,
        "Rockies": 98_261_171, "Braves": 87_622_648, "Indians": 86_339_067,
        "Pirates": 85_885_832, "Marlins": 84_637_500, "Athletics": 80_279_166,
        "Rays": 73_649_584, "Diamondbacks": 70_762_833, "Astros": 69_064_200,
    },
    2017: {
        "Los Angeles Dodgers": 242_065_828, "New York Yankees": 201_539_699,
        "Boston Red Sox": 199_805_178, "Detroit Tigers": 199_750_600,
        "Toronto Blue Jays": 177_795_368, "Texas Rangers": 175_909_063,
        "San Francisco Giants": 172_354_611, "Chicago Cubs": 172_189_880,
        "Washington Nationals": 167_846_918, "Baltimore Orioles": 163_676_616,
        "Los Angeles Angels of Anaheim": 160_375_333, "New York Mets": 155_187_460,
        "Seattle Mariners": 154_800_918, "St. Louis Cardinals": 152_452_933,
        "Kansas City Royals": 140_925_250, "Colorado Rockies": 130_963_571,
        "Cleveland Indians": 124_861_165, "Houston Astros": 124_343_900,
        "Atlanta Braves": 112_437_541, "Miami Marlins": 111_881_100,
        "Philadelphia Phillies": 111_378_000, "Minnesota Twins": 108_077_500,
        "Pittsburgh Pirates": 100_575_946, "Chicago White Sox": 99_119_770,
        "Cincinnati Reds": 93_768_785, "Arizona Diamondbacks": 93_257_600,
        "Oakland Athletics": 81_738_333, "San Diego Padres": 71_624_400,
        "Tampa Bay Rays": 69_962_532, "Milwaukee Brewers": 63_061_300,
    },
    2018: {
        # Source quoted in $M to 2 decimals; converted to USD with $10K precision.
        "Boston Red Sox": 235_650_000, "San Francisco Giants": 208_510_000,
        "Los Angeles Dodgers": 186_140_000, "Chicago Cubs": 183_460_000,
        "Washington Nationals": 181_590_000, "Los Angeles Angels": 175_100_000,
        "New York Yankees": 168_540_000, "Seattle Mariners": 162_480_000,
        "Toronto Blue Jays": 162_316_000, "St. Louis Cardinals": 161_010_000,
        "Houston Astros": 160_040_000, "New York Mets": 154_610_000,
        "Texas Rangers": 144_000_000, "Baltimore Orioles": 143_090_000,
        "Colorado Rockies": 141_340_000, "Cleveland Indians": 134_350_000,
        "Arizona Diamondbacks": 132_500_000, "Minnesota Twins": 131_910_000,
        "Detroit Tigers": 129_920_000, "Kansas City Royals": 129_920_000,
        "Atlanta Braves": 120_540_000, "Cincinnati Reds": 101_190_000,
        "Miami Marlins": 98_640_000, "Philadelphia Phillies": 96_850_000,
        "San Diego Padres": 96_130_000, "Milwaukee Brewers": 90_240_000,
        "Pittsburgh Pirates": 87_880_000, "Tampa Bay Rays": 78_730_000,
        "Chicago White Sox": 72_180_000, "Oakland Athletics": 68_530_000,
    },
    2019: {
        "Boston Red Sox": 202_921_500, "Chicago Cubs": 205_556_714,
        "New York Yankees": 206_084_848, "Los Angeles Dodgers": 152_119_998,
        "San Francisco Giants": 178_271_237, "St. Louis Cardinals": 158_370_266,
        "Washington Nationals": 161_715_381, "Houston Astros": 159_719_666,
        "Los Angeles Angels": 158_878_583, "New York Mets": 142_149_270,
        "Seattle Mariners": 138_864_075, "Colorado Rockies": 145_932_999,
        "Philadelphia Phillies": 140_711_962, "Texas Rangers": 106_017_564,
        "Cincinnati Reds": 126_423_214, "Milwaukee Brewers": 121_530_400,
        "Arizona Diamondbacks": 107_901_831, "Minnesota Twins": 113_326_933,
        "Cleveland Indians": 118_991_701, "Detroit Tigers": 101_923_400,
        "Atlanta Braves": 113_376_043, "Toronto Blue Jays": 63_171_171,
        "Kansas City Royals": 96_547_237, "San Diego Padres": 74_033_835,
        "Oakland Athletics": 91_318_333, "Chicago White Sox": 88_312_121,
        "Pittsburgh Pirates": 74_808_002, "Baltimore Orioles": 72_682_882,
        "Miami Marlins": 71_239_714, "Tampa Bay Rays": 53_444_931,
    },
    # 2020: pre-pandemic full-year commitments from thebaseballcube.com.
    2020: {
        "New York Yankees": 214_291_339, "Houston Astros": 212_321_933,
        "Los Angeles Dodgers": 189_065_000, "Chicago Cubs": 188_959_500,
        "Los Angeles Angels": 176_329_344, "St. Louis Cardinals": 160_781_766,
        "Washington Nationals": 159_242_411, "Philadelphia Phillies": 152_877_962,
        "Atlanta Braves": 149_466_875, "San Francisco Giants": 144_994_027,
        "Cincinnati Reds": 143_143_673, "New York Mets": 142_288_337,
        "San Diego Padres": 140_317_600, "Texas Rangers": 137_834_500,
        "Colorado Rockies": 136_399_833, "Minnesota Twins": 127_610_333,
        "Chicago White Sox": 120_898_499, "Boston Red Sox": 120_361_000,
        "Milwaukee Brewers": 97_535_926, "Detroit Tigers": 96_832_300,
        "Oakland Athletics": 94_318_433, "Toronto Blue Jays": 92_582_371,
        "Cleveland Guardians": 89_004_234, "Arizona Diamondbacks": 86_471_066,
        "Kansas City Royals": 83_278_225, "Seattle Mariners": 70_343_800,
        "Tampa Bay Rays": 65_812_166, "Baltimore Orioles": 52_415_682,
        "Miami Marlins": 47_861_700, "Pittsburgh Pirates": 42_119_000,
    },
    2021: {
        "Dodgers": 235_412_876, "Yankees": 191_205_631, "Red Sox": 180_261_996,
        "Angels": 177_353_000, "Phillies": 174_009_000, "Padres": 171_686_600,
        "Astros": 171_018_567, "Mets": 167_415_024, "Nationals": 161_907_528,
        "Cubs": 149_665_500, "Blue Jays": 137_133_333, "Cardinals": 135_047_200,
        "Braves": 134_459_435, "Giants": 127_889_903, "White Sox": 125_987_500,
        "Twins": 121_003_834, "Reds": 118_748_164, "Rockies": 103_986_666,
        "Diamondbacks": 89_077_233, "Royals": 87_779_400, "Brewers": 87_569_366,
        "Rangers": 84_868_750, "Tigers": 80_398_600, "Athletics": 74_615_000,
        "Mariners": 64_553_500, "Rays": 60_388_600, "Marlins": 49_425_000,
        "Guardians": 46_833_300, "Orioles": 45_701_135, "Pirates": 35_905_000,
    },
    2022: {
        "Dodgers": 277_108_333, "Mets": 253_119_999, "Yankees": 240_290_714,
        "Phillies": 221_738_462, "Padres": 208_772_618, "Red Sox": 195_166_000,
        "White Sox": 181_660_734, "Braves": 173_935_000, "Angels": 169_413_094,
        "Blue Jays": 168_070_905, "Astros": 163_939_599, "Cardinals": 150_746_666,
        "Giants": 142_292_500, "Rangers": 134_961_333, "Cubs": 130_560_000,
        "Rockies": 129_452_166, "Brewers": 122_281_128, "Tigers": 116_040_000,
        "Nationals": 114_623_095, "Twins": 110_859_524, "Reds": 99_580_000,
        "Mariners": 92_745_714, "Diamondbacks": 75_993_333, "Rays": 75_347_813,
        "Royals": 74_110_000, "Marlins": 69_000_000, "Guardians": 42_310_000,
        "Pirates": 37_875_000, "Athletics": 32_548_334, "Orioles": 30_221_166,
    },
    2023: {
        "Mets": 334_233_332, "Yankees": 268_954_047, "Padres": 236_962_024,
        "Phillies": 232_424_939, "Dodgers": 218_332_634, "Blue Jays": 205_680_777,
        "Angels": 204_088_094, "Braves": 199_727_500, "Rangers": 183_578_160,
        "White Sox": 180_911_666, "Astros": 180_888_333, "Cubs": 180_115_000,
        "Red Sox": 175_783_182, "Giants": 175_590_000, "Rockies": 166_250_466,
        "Cardinals": 147_770_834, "Twins": 141_271_190, "Mariners": 129_814_047,
        "Diamondbacks": 112_763_571, "Brewers": 108_644_960, "Tigers": 105_338_500,
        "Reds": 86_374_500, "Marlins": 81_075_000, "Nationals": 79_983_095,
        "Royals": 75_825_000, "Guardians": 75_010_000, "Orioles": 64_907_966,
        "Rays": 64_652_911, "Pirates": 60_787_500, "Athletics": 43_145_000,
    },
    2024: {
        "Mets": 301_731_074, "Yankees": 293_666_666, "Astros": 237_303_141,
        "Phillies": 236_182_617, "Braves": 225_315_000, "Rangers": 221_955_000,
        "Blue Jays": 221_876_784, "Dodgers": 220_691_666, "Cubs": 216_330_000,
        "Giants": 188_767_909, "Cardinals": 164_301_667, "Red Sox": 162_324_847,
        "Angels": 158_818_094, "Diamondbacks": 156_511_716, "Padres": 153_765_453,
        "Rockies": 134_099_285, "Mariners": 129_158_333, "Twins": 118_886_590,
        "White Sox": 117_773_333, "Royals": 105_219_570, "Nationals": 95_371_429,
        "Tigers": 95_073_933, "Orioles": 94_495_168, "Brewers": 94_484_960,
        "Reds": 88_123_333, "Rays": 88_066_012, "Guardians": 86_433_928,
        "Marlins": 83_710_000, "Pirates": 72_014_000, "Athletics": 47_905_000,
    },
    2025: {
        "Los Angeles Dodgers": 321_000_000, "New York Mets": 315_000_000,
        "Philadelphia Phillies": 278_000_000, "New York Yankees": 272_000_000,
        "Toronto Blue Jays": 233_000_000, "Texas Rangers": 206_000_000,
        "Houston Astros": 204_000_000, "Atlanta Braves": 202_000_000,
        "San Diego Padres": 197_000_000, "Los Angeles Angels": 192_000_000,
        "Boston Red Sox": 184_000_000, "Chicago Cubs": 184_000_000,
        "Arizona Diamondbacks": 174_000_000, "San Francisco Giants": 158_000_000,
        "Baltimore Orioles": 150_000_000, "Seattle Mariners": 138_000_000,
        "Minnesota Twins": 137_000_000, "Detroit Tigers": 131_000_000,
        "St. Louis Cardinals": 122_000_000, "Kansas City Royals": 113_000_000,
        "Colorado Rockies": 112_000_000, "Cincinnati Reds": 103_000_000,
        "Washington Nationals": 100_000_000, "Milwaukee Brewers": 94_000_000,
        "Cleveland Guardians": 82_000_000, "Pittsburgh Pirates": 75_000_000,
        "Tampa Bay Rays": 73_000_000, "Chicago White Sox": 59_000_000,
        "Oakland Athletics": 55_000_000, "Miami Marlins": 47_000_000,
    },
}


def main() -> None:
    rows = []
    for season, teams in RAW.items():
        canonical_seen = set()
        for raw_name, payroll in teams.items():
            if raw_name not in SHORT_TO_FULL:
                raise KeyError(f"Unmapped team name {raw_name!r} in {season}")
            canonical = SHORT_TO_FULL[raw_name]
            if canonical in canonical_seen:
                raise ValueError(f"Duplicate canonical team {canonical} in {season}")
            canonical_seen.add(canonical)

            source = SOURCE_2020 if season == 2020 else SOURCE_DEFAULT
            notes = "pre-pandemic full-year commitment" if season == 2020 else ""
            rows.append({
                "season": season,
                "team": canonical,
                "opening_day_payroll_usd": payroll,
                "source": source,
                "notes": notes,
            })

        if len(canonical_seen) != 30:
            raise ValueError(
                f"Season {season} produced {len(canonical_seen)} unique teams, expected 30"
            )

    rows.sort(key=lambda r: (r["season"], r["team"]))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["season", "team", "opening_day_payroll_usd", "source", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    expected = 30 * len(RAW)
    print(f"Wrote {len(rows)} rows (expected {expected}) to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
