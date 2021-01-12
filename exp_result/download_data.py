from packaging import version
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns
from scipy import stats
import tensorboard as tb

major_ver, minor_ver, _ = version.parse(tb.__version__).release
assert major_ver >= 2 and minor_ver >= 3, \
    "This notebook requires TensorBoard 2.3 or later."
print("TensorBoard version: ", tb.__version__)

url = [("no_clipping_no_framestack", "BXWKsOClSESqR9ZTxIDvpQ"),
       ("no_clipping", "T815gfawS1SvBT1CpSwjaA"),
       ("original_stack16_exp", "Mlh8M5eVReOSR53LOA1WKw"),
       ("duel_exp", "8xRTkK91TOqKux7j8ILVOg"),
       ("original_exp", "E2liJk1GT7Sxf9h7ZPq3Jw"),
       ("original_stack8_exp", "8xRTkK91TOqKux7j8ILVOg")
       ]
for exp in url:
    experiment = tb.data.experimental.ExperimentFromDev(exp[1])
    data = experiment.get_scalars()
    data.to_csv("./raw/{}.csv".format(exp[0]), index=False)
    print("sucessfully download: {}".format(exp[0]))