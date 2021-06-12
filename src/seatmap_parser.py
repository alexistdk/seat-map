import re
import xml.etree.ElementTree as ET
import argparse
import json
from pathlib import Path


class Seat:
    def __init__(self, cabin_type, availability, element_type, _id, price=None):
        self._cabin_type = cabin_type
        self._availability = availability
        self._element_type = element_type
        self._id = _id
        self._price = price

    @property
    def price(self): return self._price

    @price.setter
    def price(self, new_price):
        self.price = new_price

    def get_data(self):
        data = {
            'Element Type': self._element_type,
            'Seat Id': self._id,
            'Cabin Class': self._cabin_type,
            'Availability': self._availability,
        }

        if self._price:
            data['Price'] = self._price

        return data


class XMLParser:
    @classmethod
    def parse(cls, xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        if xml_file == 'seatmap1.xml':
            seat_map = cls.parse_xml1(root)
            cls.write_json(seat_map, xml_file)
        """
        namespace = cls.get_namespace(root)
        prices = cls.get_prices(root, namespace)
        seat_maps = cls.get_seat_maps(root, namespace)
        print(seat_maps)
        """

    @staticmethod
    def write_json(data, filename):
        json_filename = filename.replace('xml', 'json')
        with open(json_filename, 'w') as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def get_responses(root):
        for namespace in root:
            for ns in namespace.iter():
                tag_name = ns.tag.split('}')[1]
                if tag_name == 'SeatMapResponse':
                    return ns.tag

    @classmethod
    def parse_xml1(cls, root):
        responses = cls.get_responses(root)
        namespace = cls.get_namespace(responses)
        rows = []
        seat_map_responses = root.iter(responses)
        for seat_map in seat_map_responses:
            sm_detail = seat_map[1]
            for cabin in sm_detail:
                for row in cabin:
                    cabin_type = row.attrib.get('CabinType')
                    row_number = row.attrib.get('RowNumber')
                    seats = []
                    for seat in row:
                        seat_info = seat.findall(namespace + 'Summary')
                        if seat_info:
                            seat_info = seat_info[0]
                            seat_id = seat_info.attrib.get('SeatNumber')
                            available = not seat_info.attrib.get('OccupiedInd')
                            element_type = 'Seat'
                            price = cls.get_price(seat, namespace, 'Service')
                            seat_data = Seat(cabin_type, available, element_type, seat_id, price=price)
                            seats.append(seat_data.get_data())
                    rows.append({'Row Number': row_number, 'Seats': seats})
        return {'Rows': rows}

    @staticmethod
    def get_price(seat, namespace, tag):
        preferred = seat.findall(namespace + tag)
        if preferred:
            preferred = preferred[0]
            if preferred.attrib.get('CodeContext') == 'Preferred':
                return int(preferred[0].attrib.get('Amount'))
        return None


    """
        column_number = seat.attrib.get('ColumnNumber')
        for child in seat.iter():
            namespace = cls.get_namespace(responses)
            if namespace + 'Summary' == child.tag:
                available = not child.attrib.get('OccupiedInd')
                seat_id = child.attrib.get('SeatNumber')
                seat_info = Seat(cabin_type, column_number, available, 'Seat', seat_id)
                seats.append(seat_info.get_data())
            if namespace + 'Service' == child.tag:
                pass
                
    row_info = {'Row Number': row_number, 'Seats': seats}
    rows.append(row_info)
    """

    @staticmethod
    def is_preferred(seat): pass

    @staticmethod
    def get_namespace(element):
        if isinstance(element, str):
            return re.sub(r'[A-Za-z]+$', '', element)
        return re.sub(r'[A-Za-z]+$', '', element.tag)

    @staticmethod
    def get_tag_name(tag): return tag.split('}')[1]

    @staticmethod
    def get_prices(root, namespace):
        prices = root.findall(namespace + 'ALaCarteOffer')[0]
        prices_list = []
        for offer in prices:
            offer_id = offer.attrib.get('OfferItemID')
            for item in offer:
                if 'UnitPriceDetail' in item.tag:
                    for child in item.iter():
                        if child.tag == namespace + 'SimpleCurrencyPrice':
                            price = float(child.text)
                            currency = child.attrib.get('Code')
                            prices_list.append({'OfferId': offer_id, 'Currency': currency, 'Price': price})
        return prices_list

    @staticmethod
    def get_seat_maps(root, namespace):
        seat_maps = root.findall(namespace + 'SeatMap')
        positions = []
        for seat_map in seat_maps:
            segment = namespace + 'SegmentRef'
            for cabin in seat_map.iter():
                if segment == cabin.tag:
                    segment = cabin.text
                if 'CabinLayout' in cabin.tag:
                    for column in cabin.iter():
                        if column.tag == namespace + 'Columns':
                            place = column.text
                            position = column.attrib.get('Position')
                            positions.append({'Segment': segment, 'Place': place, 'Position': position})
        return positions


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parse = argparse.ArgumentParser()
    parse.add_argument('file', help='XML file to parse', type=str)
    file = None
    try:
        args = parse.parse_args()
        file = args.file
    except Exception as e:
        print("Wrong argument. It has to be a file")
        print(f"Error: {e}")

    if file:
        parser = XMLParser()
        parser.parse(file)
