from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from openaix.coordinates import (format_icao_dm, format_icao_dms, format_mgrs, format_packed_dms, packed_dms_value,
                                 parse, parse_icao, parse_mgrs, parse_packed_dms)


class PackedDmsTests(unittest.TestCase):
    def test_parse(self):
        latitude, longitude = parse("N40154835W104460637")
        self.assertAlmostEqual(latitude, 40 + 15 / 60 + 48.35 / 3600, places=10)
        self.assertAlmostEqual(longitude, -(104 + 46 / 60 + 6.37 / 3600), places=10)
        self.assertEqual(parse(" n40154835 w104460637 "), (latitude, longitude))

    def test_ten_thousandths_of_a_second(self):
        self.assertAlmostEqual(packed_dms_value("N3950567812"), 39 + 50 / 60 + 56.7812 / 3600, places=10)
        self.assertAlmostEqual(packed_dms_value("W10441478312"), -(104 + 41 / 60 + 47.8312 / 3600), places=10)

    def test_round_trip(self):
        for text in ("N40154835W104460637", "S33513025E151125512", "N00000000E000000000", "S89595999W179595999",
                     "N90000000E180000000", "S90000000W180000000", "N00000001W000000001"):
            with self.subTest(text=text):
                self.assertEqual(format_packed_dms(*parse(text)), text)

    def test_hemisphere_edges(self):
        self.assertEqual(format_packed_dms(0, 0), "N00000000E000000000")
        self.assertEqual(format_packed_dms(-0.0, -0.0), "N00000000E000000000")
        # A value that rounds to zero has no sign.
        self.assertEqual(format_packed_dms(-1e-9, -1e-9), "N00000000E000000000")
        self.assertEqual(format_packed_dms(90, 180), "N90000000E180000000")
        self.assertEqual(format_packed_dms(-90, -180), "S90000000W180000000")
        self.assertEqual(parse("S00000000W000000000"), (0, 0))

    def test_rounding_carry(self):
        # 59.996 seconds rounds to the next minute, and 59 minutes 59.996 seconds to the next degree.
        self.assertEqual(format_packed_dms(10 + 59 / 60 + 59.996 / 3600, -(20 + 59.996 / 3600)), "N11000000W020010000")
        self.assertEqual(format_packed_dms(-(89 + 59 / 60 + 59.999 / 3600), 179 + 59 / 60 + 59.999 / 3600),
                         "S90000000E180000000")

    def test_invalid(self):
        for text in ("X40154835W104460637", "N40154835N104460637", "E40154835W104460637", "N4015483W104460637",
                     "N401548351W104460637", "N40604835W104460637", "N40156035W104460637", "N91000000W104460637",
                     "N90000001W104460637", "N40154835W180000001", "N40154835W190000000", "N40154835W10446063",
                     "N40154835", "N4015483AW104460637", ""):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse(text)
        for value in ("N401548", "S90000001", "Q40154835", "W1044606"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    packed_dms_value(value)
        for latitude, longitude in ((90.01, 0), (0, -180.01), (float("nan"), 0)):
            with self.subTest(latitude=latitude, longitude=longitude):
                with self.assertRaises(ValueError):
                    format_packed_dms(latitude, longitude)


class IcaoTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse("401548N1044606W"), parse_icao("401548N1044606W"))
        latitude, longitude = parse("401548N1044606W")
        self.assertAlmostEqual(latitude, 40 + 15 / 60 + 48 / 3600, places=10)
        self.assertAlmostEqual(longitude, -(104 + 46 / 60 + 6 / 3600), places=10)
        self.assertEqual(parse("4015N10446W"), (40.25, round(-(104 + 46 / 60), 10)))

    def test_round_trip(self):
        for text in ("401548N1044606W", "335130S1511255E", "000000N0000000E", "900000N1800000E", "900000S1800000W"):
            with self.subTest(text=text):
                self.assertEqual(format_icao_dms(*parse(text)), text)
        for text in ("4015N10446W", "3351S15112E", "0000N00000E", "9000S18000W", "8959N17959E"):
            with self.subTest(text=text):
                self.assertEqual(format_icao_dm(*parse(text)), text)

    def test_rounding_carry(self):
        self.assertEqual(format_icao_dms(10 + 59 / 60 + 59.6 / 3600, -(20 + 59.5 / 3600)), "110000N0200100W")
        self.assertEqual(format_icao_dm(-(89 + 59.7 / 60), 179 + 59.5 / 60), "9000S18000E")
        self.assertEqual(format_icao_dm(40 + 15.4 / 60, -(104 + 45.6 / 60)), "4015N10446W")

    def test_hemisphere_edges(self):
        self.assertEqual(format_icao_dms(-0.0001, -0.0001), "000000N0000000E")
        self.assertEqual(format_icao_dms(-0.0003, -0.0003), "000001S0000001W")

    def test_invalid(self):
        for text in ("401548X1044606W", "401548N1044606N", "401548S1044606S", "406048N1044606W", "401560N1044606W",
                     "4015N1044606W", "401548N10446W", "40154N1044606W", "910000N1044606W", "401548N1810000W",
                     "6015N18060E", "4015N"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse(text)


class MgrsTests(unittest.TestCase):
    # Expected references agree with NGA GEOTRANS (the `mgrs` package) and the UTM easting and northing with PROJ.
    KNOWN = (((38.8895, -77.0352), "18SUJ2348606483"),  # Washington Monument
             ((39.861656, -104.673178), "13SEE2795312453"),
             ((-33.8568, 151.2153), "56HLH3490052288"),
             ((51.4778, -0.0015), "30UYC0821307224"),
             ((60.39, 5.32), "32VKN9723000510"),  # Norway exception: zone 32V
             ((56.5, 3.5), "32VJH6162275290"),
             ((78.22, 15.65), "33XWG1481383004"),  # Svalbard exception
             ((72.5, 8.9), "31XFA9773754424"),
             ((0.0, 0.0), "31NAA6602100000"),
             ((-80.0, 0.0), "31CDM4186716915"),
             ((84.0, 0.0), "31XDP6500529005"),
             ((-0.5, 179.9), "60MZE2282344663"))

    def test_known_points(self):
        for (latitude, longitude), text in self.KNOWN:
            with self.subTest(text=text):
                self.assertEqual(format_mgrs(latitude, longitude), text)
                parsed = parse(text)
                # The reference is the south-west corner of its 1 m square.
                self.assertLess(abs(parsed[0] - latitude), 2e-5)
                self.assertLess(abs(parsed[1] - longitude), 1e-4)

    def test_round_trip(self):
        # A square on a zone edge or at the 80S limit has its south-west corner outside the zone, so the corner
        # formats in the next zone. Round trips use the inner points only.
        for _, text in self.KNOWN:
            if text[:3] in ("32V", "31N", "31X", "31C"):
                continue
            for digits in range(6):
                short = text[:5] + text[5:10][:digits] + text[10:][:digits]
                with self.subTest(text=short):
                    self.assertEqual(format_mgrs(*parse_mgrs(short), digits), short)
        self.assertEqual(parse(" 18S UJ 23486 06483 "), parse_mgrs("18SUJ2348606483"))

    def test_precision(self):
        self.assertEqual(format_mgrs(38.8895, -77.0352, 3), "18SUJ234064")
        self.assertEqual(format_mgrs(38.8895, -77.0352, 0), "18SUJ")

    def test_invalid(self):
        for text in ("18SUJ234860648", "61SUJ2348606483", "00SUJ2348606483", "18IUJ2348606483", "18SAJ2348606483",
                     "18SUW2348606483", "18AUJ2348606483", "18SUJ234860648312", "18SMN2348606483"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse(text)
        for latitude in (84.5, -80.5):
            with self.assertRaises(ValueError):
                format_mgrs(latitude, 0)
        with self.assertRaises(ValueError):
            format_mgrs(0, 0, 6)


class DetectionTests(unittest.TestCase):
    def test_one_position_in_every_format(self):
        latitude, longitude = 39 + 51 / 60 + 42 / 3600, -(104 + 40 / 60 + 23.4 / 3600)
        for text in (format_packed_dms(latitude, longitude), format_icao_dms(latitude, longitude),
                     format_icao_dm(latitude, longitude), format_mgrs(latitude, longitude)):
            with self.subTest(text=text):
                parsed = parse(text)
                self.assertLess(abs(parsed[0] - latitude), 0.01)
                self.assertLess(abs(parsed[1] - longitude), 0.01)

    def test_unknown_format(self):
        for text in ("39.86, -104.67", "hello", "N40154835W104460637X"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse(text)
        self.assertEqual(parse_packed_dms("N40154835W104460637"), parse("N40154835W104460637"))


if __name__ == "__main__":
    unittest.main()
