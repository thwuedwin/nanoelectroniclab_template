# -*- coding: utf-8 -*-
'''
Created by thwuedwin <thwuedwin@gmail.com>, Apr 2026
'''
from qcodes.instrument import VisaInstrument
from qcodes import validators as vals

class OxfordMercuryiTC(VisaInstrument):
    def __init__(
            self, name: str, address: str, **kwargs: "Unpack[VisaInstrumentKWArgs]"
    ):
        super().__init__(name, address, terminator='\n', **kwargs)

        self.connect_message()

if __name__ == '__main__':
    itc = OxfordMercuryiTC('itc', 'TCPIP0::192.168.50.207::7020::SOCKET')
