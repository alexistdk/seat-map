import re
import xml.etree.ElementTree as ET
import argparse
import json


class Seat:
    def __init__(self, cabin_type, availability, element_type, _id, price=None, currency=None, info_extra=None):
        self._cabin_type = cabin_type
        self._availability = availability
        self._element_type = element_type
        self._id = _id
        self._price = price
        self._currency = currency
        self._info_extra = info_extra

    def get_data(self):
        data = {
            'Element Type': self._element_type,
            'Seat Id': self._id,
            'Cabin Class': self._cabin_type,
            'Availability': self._availability,
        }

        if self._price:
            data['Price'] = self._price
            data['Currency'] = self._currency

        if self._info_extra:
            data['Info Extra'] = self._info_extra

        return data


class XMLParser:
    @classmethod
    def parse(cls, xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        if xml_file == 'seatmap1.xml':
            seat_map = SeatMap1.parse_xml(root)
        else:
            seat_map = SeatMap2.parse_xml(root)
        cls.write_json(seat_map, xml_file)

    @staticmethod
    def get_namespace(element):
        if isinstance(element, str):
            return re.sub(r'[A-Za-z]+$', '', element)
        return re.sub(r'[A-Za-z]+$', '', element.tag)

    @staticmethod
    def write_json(data, filename):
        json_filename = filename.replace('xml', 'json')
        with open(json_filename, 'w') as f:
            json.dump(data, f, indent=4)


class SeatMap1:
    @classmethod
    def parse_xml(cls, root):
        responses = cls.get_responses(root)
        namespace = XMLParser.get_namespace(responses)
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
                            price = cls.get_data_price(seat, namespace, 'Amount')
                            currency = cls.get_data_price(seat, namespace, 'CurrencyCode')
                            seat_data = Seat(cabin_type, available, element_type, seat_id, price=price,
                                             currency=currency)
                            seats.append(seat_data.get_data())
                    rows.append({'Row Number': row_number, 'Seats': seats})
        return {'Rows': rows}

    @staticmethod
    def get_responses(root):
        for namespace in root:
            for ns in namespace.iter():
                tag_name = ns.tag.split('}')[1]
                if tag_name == 'SeatMapResponse':
                    return ns.tag

    @staticmethod
    def get_data_price(seat, namespace, attribute):
        preferred = seat.findall(namespace + 'Service')
        if preferred:
            preferred = preferred[0]
            if preferred.attrib.get('CodeContext') == 'Preferred':
                return int(preferred[0].attrib.get(attribute))
        return None


class SeatMap2:
    @classmethod
    def parse_xml(cls, root):
        namespace = XMLParser.get_namespace(root)
        rows = cls.get_seats(root, namespace)
        return {'Rows': rows}

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

    @classmethod
    def get_seats(cls, root, namespace):
        definitions_list = cls.get_definitions(root, namespace)
        prices = cls.get_prices(root, namespace)
        seat_maps = root.findall(namespace + 'SeatMap')
        data_seats = []
        data_rows = []
        for seat_map in seat_maps:
            cabin = seat_map[1]
            rows = cabin.findall(namespace + 'Row')
            for row in rows:
                number = row[0].text
                for seat in row.iter():
                    if namespace + 'Seat' == seat.tag:
                        column = seat[0].text
                        seat_id = number + column
                        definitions = cls.get_extra_info(definitions_list, seat, namespace)
                        price_dict = cls.get_info_price(seat, namespace, prices)
                        available = cls.is_available(seat, namespace)
                        if price_dict:
                            price = price_dict['Price']
                            currency = price_dict['Currency']
                            seat_data = Seat(cabin_type='NA', availability=available, element_type='Seat', _id=seat_id,
                                             info_extra=definitions, price=price, currency=currency)
                        else:
                            seat_data = Seat(cabin_type='NA', availability=available, element_type='Seat', _id=seat_id,
                                             info_extra=definitions)
                        data_seats.append(seat_data.get_data())
                data_rows.append({'Row': number, 'Seats': data_seats})
        return data_rows

    @staticmethod
    def get_info_price(seat, namespace, prices):
        price = seat.findall(namespace + 'OfferItemRefs')
        if price:
            price_id = price[0].text
            for offer in prices:
                if offer['OfferId'] == price_id:
                    return offer
        return None

    @staticmethod
    def get_extra_info(info_extra, seat, namespace):
        definition_refs = seat.findall(namespace + 'SeatDefinitionRef')
        definitions = [definition.text for definition in definition_refs]
        list_extra_info = []
        index = 0
        for definition in definitions:
            for info in info_extra:
                if definition == info['Id']:
                    list_extra_info.append(info['Description'])
                index += 1
        return list_extra_info

    @staticmethod
    def is_available(seat, namespace):
        definition_refs = seat.findall(namespace + 'SeatDefinitionRef')
        definitions = [definition.text for definition in definition_refs]
        return 'SD4' in definitions and 'SD11' not in definitions

    @classmethod
    def get_definitions(cls, root, namespace):
        definition_list = []
        data_list = root.findall(namespace + 'DataLists')[0]

        service_definitions_list = data_list.findall(namespace + 'ServiceDefinitionList')[0]
        for definition in service_definitions_list.findall(namespace + 'ServiceDefinition'):
            definition_id = definition.attrib.get('ServiceDefinitionID')
            def_text = cls.get_service_definition_text(namespace, definition)
            definition_list.append({'Id': definition_id, 'Description': def_text})

        seat_definitions = data_list.findall(namespace + 'SeatDefinitionList')[0]
        for definition in seat_definitions.findall(namespace + 'SeatDefinition'):
            definition_id = definition.attrib.get('SeatDefinitionID')
            def_text = cls.get_seat_definition_text(namespace, definition)
            definition_list.append({'Id': definition_id, 'Description': def_text})
        return definition_list

    @staticmethod
    def get_service_definition_text(namespace, definition):
        def_text = definition.findall(namespace + 'Descriptions')[0]
        return def_text.findall(namespace + 'Description')[0][0].text

    @staticmethod
    def get_seat_definition_text(namespace, definition):
        definition_text = definition.findall(namespace + 'Description')[0]
        return definition_text.findall(namespace + 'Text')[0].text


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
