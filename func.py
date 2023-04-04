import pandas as pd
import numpy as np
from decimal import Decimal
import matplotlib.pyplot as plt

def sep_midpoints_endpoints(R_constr, R_use):
    '''
    Separating midpoints and endpoints of the results from ecos_sep_constr_use
    :param R_constr: R matrix for construction activities
    :param R_use: R matrix for use activities
    :return: R_constr_midpoint, R_use_midpoint, R_constr_endpoint, R_use_endpoint
    '''
    R_constr_midpoint = R_constr.copy(deep = True)
    R_use_midpoint = R_use.copy(deep = True)
    R_constr_endpoint = R_constr.copy(deep = True)
    R_use_endpoint = R_use.copy(deep = True)
    R_constr_midpoint.drop(R_constr_midpoint[(R_constr_midpoint["CF unit"].str.contains("PDF.m2.yr")) | (R_constr_midpoint["CF unit"].str.contains("DALY"))].index, inplace=True)
    R_use_midpoint.drop(R_use_midpoint[(R_use_midpoint["CF unit"].str.contains("PDF.m2.yr")) | (R_use_midpoint["CF unit"].str.contains("DALY"))].index, inplace=True)
    R_constr_endpoint.drop(R_constr_endpoint[~(R_constr_endpoint["CF unit"].str.contains("PDF.m2.yr")) & ~(R_constr_endpoint["CF unit"].str.contains("DALY"))].index, inplace=True)
    R_use_endpoint.drop(R_use_endpoint[~(R_use_endpoint["CF unit"].str.contains("PDF.m2.yr")) & ~(R_use_endpoint["CF unit"].str.contains("DALY"))].index, inplace=True)
    return R_constr_midpoint, R_use_midpoint, R_constr_endpoint, R_use_endpoint

def impact_categories(R_constr, R_use):
    '''
    Generating lists of midpoints and endpoints (both for HH and EQ) impact categories
    :param R_constr: R matrix for construction activities
    :param R_use: R matrix for use activities
    :return: midpoint_categories, endpoint_categories_HH, endpoint_categories_EQ
    '''
    R_constr_mid, R_use_mid, R_constr_end, R_use_end = sep_midpoints_endpoints(R_constr=R_constr, R_use=R_use)

    midpoint_categories = list(R_use_mid["Impact category"].unique())
    endpoint_categories_EQ = list(R_use_end[R_use_end["CF unit"] == "PDF.m2.yr"]["Impact category"].unique())
    endpoint_categories_HH = list(R_use_end[R_use_end["CF unit"] == "DALY"]["Impact category"].unique())

    return midpoint_categories, endpoint_categories_HH, endpoint_categories_EQ

def impact_computation(tech, impact, conversion_factor, capacity_factor, use_value, indicator, format,
                       R_constr, R_use):
    '''
    Compute the impact of a technology for a given impact category.
    :param tech: name of the technology
    :param impact: name of the impact category
    :param conversion_factor: value of conversion factor between ES and LCIA units
    :param capacity_factor: value of capacity factor between ES and LCIA output values
    :param use_value: amount for the use phase (construction phase is 1 unit)
    :param indicator: "midpoint", "endpoint" or "aop"
    :param format: "clean" if cleaned text "number" if float value is needed
    :param R_constr_mid: R matrix for construction activities for midpoints only
    :param R_use_mid: R matrix for use activities for midpoints only
    :param R_constr_end: R matrix for construction activities for endpoints only
    :param R_use_end: R matrix for use activities for endpoints only
    :return: either a text or the float of the impact computation
    '''

    R_constr_mid, R_use_mid, R_constr_end, R_use_end = sep_midpoints_endpoints(R_constr=R_constr, R_use=R_use)

    if indicator == "aop": # Areas of protection (HH, EQ)
        # Use phase for EQ
        ecosystem_quality_use = (float(R_use_end[(R_use_end.ES_name == tech) & (R_use_end["CF unit"].str.contains("PDF.m2.yr"))].value.sum()) / conversion_factor) * use_value

        # Use phase for HH
        human_health_use = (float(R_use_end[(R_use_end.ES_name == tech) & (R_use_end["CF unit"].str.contains("DALY"))].value.sum()) / conversion_factor) * use_value

        # Construction phase for EQ
        ecosystem_quality_constr = float(R_constr_end[(R_constr_end.ES_name == tech) & (R_constr_end["CF unit"].str.contains("PDF.m2.yr"))].value.sum()) * capacity_factor

        # Construction phase for HH
        human_health_constr = float(R_constr_end[(R_constr_end.ES_name == tech) & (R_constr_end["CF unit"].str.contains("DALY"))].value.sum()) * capacity_factor

        if format == "clean": # returns under text format
            return f"Ecosystem quality: {'%.4e' % Decimal(ecosystem_quality_constr+ecosystem_quality_use)} PDF.m2.yr", f"Human health: {'%.4e' % Decimal(human_health_constr+human_health_use)} DALY"

        elif format == "number": # returns as a float
            return [ecosystem_quality_constr + ecosystem_quality_use, human_health_constr + human_health_use]

    # Midpoint and endpoint levels
    elif indicator == "midpoint":
        df_constr = R_constr_mid.copy()
        df_use = R_use_mid.copy()
    elif indicator == "endpoint":
        df_constr = R_constr_end.copy()
        df_use = R_use_end.copy()

    unit = df_constr[(df_constr["Impact category"] == impact)]["CF unit"].iloc[0]

    # Construction
    constr = float(df_constr[(df_constr.ES_name == tech) & (df_constr["Impact category"] == impact)].value * capacity_factor)

    # Use
    use = float(df_use[(df_use.ES_name == tech) & (df_use["Impact category"] == impact)].value / conversion_factor) * use_value

    # Total
    if format == "clean":
        return f"{impact}: {'%.4e' % Decimal(use+constr)} {unit}"

    elif format == "number":
        return use + constr

def comparison(tech, conversion_factor, capacity_factor, use_value, indicator, df_bw_mid, df_bw_end,
               R_constr, R_use):

    '''

    :param tech: str, technology name
    :param conversion_factor: float, conversion factor
    :param capacity_factor: float, capacity factor
    :param use_value: float, value representing the use phase (e.g., 1 GWh)
    :param indicator: str, "midpoint", "endpoint" or "aop"
    :param df_bw_mid: dataframe of brightway results for midpoints
    :param df_bw_end: dataframe of brightway results for midpoints
    :return: dataframe containing brightway results, ecos_sep_use_constr results and the delta between them
    '''

    R_constr_mid, R_use_mid, R_constr_end, R_use_end = sep_midpoints_endpoints(R_constr=R_constr, R_use=R_use)

    midpoint_categories, endpoint_categories_HH, endpoint_categories_EQ = impact_categories(R_constr=R_constr, R_use=R_use)

    method_endpoint_EQ = "IMPACT World+ Damage 2.0 | Ecosystem quality | "
    method_endpoint_HH = "IMPACT World+ Damage 2.0 | Human health | "
    method_midpoint = "IMPACT World+ Midpoint 2.0 | Midpoint | "

    es_moo = []
    brightway = []

    if indicator == "aop":

        HH_brightway = 0
        EQ_brightway = 0

        for impact in endpoint_categories_EQ:
            EQ_brightway+=df_bw_end[f"{method_endpoint_EQ}{impact}"].iloc[0]

        for impact in endpoint_categories_HH:
            HH_brightway+=df_bw_end[f"{method_endpoint_HH}{impact}"].iloc[0]

        EQ_ES_moo, HH_ES_moo = impact_computation(tech=tech, impact=None, conversion_factor=conversion_factor, capacity_factor=capacity_factor, use_value=use_value, indicator=indicator, format="number", R_constr=R_constr, R_use=R_use)

        res = pd.DataFrame(data = [[HH_ES_moo, EQ_ES_moo], [HH_brightway, EQ_brightway]], index = ["es_moo", "brightway"], columns = ["Human health", "Ecosystem quality"])

    if indicator == "midpoint":

        for impact in midpoint_categories:
            brightway.append(df_bw_mid[f"{method_midpoint}{impact}"].iloc[0])
            es_moo.append(impact_computation(tech=tech, impact=impact, conversion_factor=conversion_factor, capacity_factor=capacity_factor, use_value=use_value, indicator=indicator, format="number", R_constr=R_constr, R_use=R_use))

        res = pd.DataFrame(data = [es_moo, brightway], index = ["es_moo", "brightway"], columns = midpoint_categories)

    if indicator == "endpoint":

        for impact in endpoint_categories_HH:
            brightway.append(df_bw_end[f"{method_endpoint_HH}{impact}"].iloc[0])
            es_moo.append(impact_computation(tech=tech, impact=impact, conversion_factor=conversion_factor, capacity_factor=capacity_factor, use_value=use_value, indicator=indicator, format="number", R_constr=R_constr, R_use=R_use))

        for impact in endpoint_categories_EQ:
            brightway.append(df_bw_end[f"{method_endpoint_EQ}{impact}"].iloc[0])
            es_moo.append(impact_computation(tech=tech, impact=impact, conversion_factor=conversion_factor, capacity_factor=capacity_factor, use_value=use_value, indicator=indicator, format="number", R_constr=R_constr, R_use=R_use))

        res = pd.DataFrame(data = [es_moo, brightway], index = ["es_moo", "brightway"], columns = endpoint_categories_HH + endpoint_categories_EQ)

    res = res.T

    res["delta"] = (res.brightway - res.es_moo) / res.brightway

    return res

def get_df_name(df):
    name =[x for x in globals() if globals()[x] is df][0]
    return name

def plot_comparison(df_comparison, save):
    plt.rcParams["axes.axisbelow"] = False
    plt.bar(x = np.linspace(0, df_comparison.shape[0], df_comparison.shape[0]),
            height=100*df_comparison.delta, tick_label = list(df_comparison.index), alpha=0.50)
    plt.ylabel("Difference between Brightway\nand ES_MOO values [%]")
    plt.grid(visible=False)
    plt.xticks(rotation=90, va="bottom")
    plt.tick_params(axis="x",direction="in", pad=-10)
    if save:
        df_name = get_df_name(df=df_comparison)
        plt.savefig(f"pics/{df_name}.pdf", format="pdf")
    plt.show()