import pandas as pd

from financial_statements.parser.sec_api.parser_utils import period_label


# convert XBRL-JSON of cash flow to pandas dataframe
def get_cash_flow_statement(xbrl_json):
    cash_flows_store = {}

    for usGaapItem in xbrl_json['StatementsOfCashFlows']:
        values = []
        indicies = []

        for fact in xbrl_json['StatementsOfCashFlows'][usGaapItem]:
            # only consider items without segment.
            if 'segment' not in fact:
                # check if date instant or date range is present
                if "instant" in fact['period']:
                    index = fact['period']['instant']
                else:
                    index = period_label(fact['period']['startDate'], fact['period']['endDate'])

                # avoid duplicate indicies with same values
                if index in indicies:
                    continue

                if "value" not in fact:
                    values.append(0)
                else:
                    values.append(fact['value'])

                indicies.append(index)

        cash_flows_store[usGaapItem] = pd.Series(values, index=indicies)

    cash_flows = pd.DataFrame(cash_flows_store)
    return cash_flows.T
