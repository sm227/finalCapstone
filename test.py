import mojito
import pprint



# with open("../../koreainvestment.key") as f:
#     lines = f.readlines()
#
# key = lines[0].strip()
# secret = lines[1].strip()
# acc_no = lines[2].strip()

broker = mojito.KoreaInvestment(
    api_key="PS2osgVtJebLijhOGFbRwYiw9lKwXQfK8PEk",
    api_secret="TcmO8QRKiSVA+ZQIV8+mXXYdbPM1iMVZrChj5X4Pi83EhBV2YLlPDnWsn5zfi3OCLyQ1quEoBYpH262PxWlbSVPuA7YaSR5MGGnE9/cCter0+CY9jfGH/sbkdIgF/fCjgi5zKLg1J84lpuAy+Dr6UCAWfvtnkXLnkZuPKB5Jz+gsmp/arVE=",
    acc_no="50117588-01"
)
resp = broker.fetch_balance()
pprint.pprint(resp)
