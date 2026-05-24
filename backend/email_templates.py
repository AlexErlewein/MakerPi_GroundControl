"""HTML email templates for GroundControl notifications"""

from typing import Optional

_BASE_STYLE = """
   body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #222; }
   h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 8px; }
   table { width: 100%; border-collapse: collapse; margin: 16px 0; }
   th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
   th { background: #f5f5f5; font-weight: bold; }
   .total-row td { font-weight: bold; font-size: 1.05em; background: #f9f9f9; }
   .btn { display: inline-block; background: #007bff; color: #fff; padding: 10px 22px;
          text-decoration: none; border-radius: 4px; margin: 12px 0; }
   .footer { color: #888; font-size: 0.85em; margin-top: 28px; border-top: 1px solid #eee; padding-top: 12px; }
   .logo { max-width: 200px; margin: 0 auto 20px; display: block; }
   .logo svg { width: 100%; height: auto; display: block; }
   .logo-text { font-size: 0.8em; color: #666; text-align: center; margin-top: 4px; }
"""

_H3CKE_LOGO_B64 = "PHN2ZyB2aWV3Qm94PSIwIDAgNTg4OS4zMSAzNjAwIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGRhdGEtbmFtZT0iRWJlbmUgMSIgaWQ9IkViZW5lXzEiPgogICAgPGRlZnM+CiAgICAgIDxzdHlsZT4KICAgICAgICAuY2xzLTEgeyBmaWxsOiAjYjc0MTBlOyB9CiAgICAgICAgLmNscy0yIHsgZmlsbDogZ3JheTsgfQogICAgICA8L3N0eWxlPgogICAgPC9kZWZzPgogICAgPHJlY3QgaGVpZ2h0PSIxMjI0IiB3aWR0aD0iMTE1LjIiIHk9IjIzNzYiIHg9IjM0ODQuOCIgY2xhc3M9ImNscy0xIj48L3JlY3Q+CiAgICA8cmVjdCBoZWlnaHQ9IjEyMjQiIHdpZHRoPSIxMTUuMiIgeT0iMCIgeD0iMzQ4NC44IiBjbGFzcz0iY2xzLTEiPjwvcmVjdD4KICAgIDxyZWN0IHRyYW5zZm9ybT0idHJhbnNsYXRlKDE3NDIuNCAxODU3LjYpIHJvdGF0ZSgtOTApIiBoZWlnaHQ9IjM2MDAiIHdpZHRoPSIxMTUuMiIgeT0iLTE3NDIuNCIgeD0iMTc0Mi40IiBjbGFzcz0iY2xzLTEiPjwvcmVjdD4KICAgIDxyZWN0IHRyYW5zZm9ybT0idHJhbnNsYXRlKDExNS4yIDM2MDApIHJvdGF0ZSgxODApIiBoZWlnaHQ9IjM2MDAiIHdpZHRoPSIxMTUuMiIgeT0iMCIgeD0iMCIgY2xhc3M9ImNscy0xIj48L3JlY3Q+CiAgICA8cmVjdCB0cmFuc2Zvcm09InRyYW5zbGF0ZSg1MzQyLjQgMTc0Mi40KSByb3RhdGUoOTApIiBoZWlnaHQ9IjM2MDAiIHdpZHRoPSIxMTUuMiIgeT0iMTc0Mi40IiB4PSIxNzQyLjQiIGNsYXNzPSJjbHMtMSI+PC9yZWN0PgogICAgPGc+CiAgICAgIDxnPgogICAgICAgIDxwYXRoIGQ9Ik0zODUyLjEyLDI2MzdoMzkuNjNsNjEuNzEsMTQ1LjU0YzYuMSwxNC44NiwxMy4zMywzNi4yLDEzLjMzLDM2LjJoLjc3czcuMjQtMjEuMzQsMTMuMzMtMzYuMmw2MS43My0xNDUuNTRoMzkuNjFsMjEuNzIsMjY4Ljk4aC0zNy4zM2wtMTMuMzMtMTY5LjU0Yy0xLjE0LTE2LjM4LS4zOC0zOS42Mi0uMzgtMzkuNjJoLS43NnMtOC4wMSwyNC43Ni0xNC40OSwzOS42MmwtNTMuNzEsMTIxLjE1aC0zMy41MmwtNTMuMzQtMTIxLjE1Yy02LjEtMTQuNDctMTQuNDctNDAuMzgtMTQuNDctNDAuMzhoLS43N3MuMzgsMjQtLjc2LDQwLjM4bC0xMi45NiwxNjkuNTRoLTM3LjcybDIxLjcyLTI2OC45OFoiIGNsYXNzPSJjbHMtMiI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Ik00MjYxLjY4LDI3ODUuNTloOC4zOHYtMy40M2MwLTMxLjYyLTE3LjkxLTQyLjI5LTQyLjI5LTQyLjI5LTI5LjcyLDAtNTMuNzEsMTguNjctNTMuNzEsMTguNjdsLTE1LjI0LTI3LjA1czI3LjgyLTIyLjg2LDcyLjAxLTIyLjg2YzQ4Ljc3LDAsNzYuMiwyNi42Nyw3Ni4yLDc1LjQ0djEyMS45MmgtMzQuMjl2LTE4LjI5YzAtOC43Ni43Ny0xNS4yNC43Ny0xNS4yNGgtLjc3cy0xNS42MSwzOC4wOS02MS43MSwzOC4wOWMtMzMuMTUsMC02NS41My0yMC4xOS02NS41My01OC42NywwLTYzLjYyLDgzLjgyLTY2LjI5LDExNi4yLTY2LjI5Wk00MjE5LjAxLDI4ODAuODNjMzEuMjQsMCw1MS40My0zMi43Niw1MS40My02MS4zNHYtNi4xaC05LjUyYy0yNy44MiwwLTc4LjEsMS45LTc4LjEsMzYuNTcsMCwxNS42MiwxMi4xOSwzMC44NiwzNi4xOSwzMC44NloiIGNsYXNzPSJjbHMtMiI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Ik00MzYyLjI5LDI2MzdoMzYuOTV2MTQ3LjA2aDI3LjA1bDUyLjU5LTcwLjg2aDQxLjkxbC02NC4wMSw4NC45NnYuNzZsNzEuMjQsMTA3LjA2aC00My4wNWwtNTcuOTEtOTAuNjdoLTI3LjgydjkwLjY3aC0zNi45NXYtMjY4Ljk4WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTQ2NDIuNjgsMjcwOC42MmM1NC40OCwwLDgzLjQ0LDQwLjM5LDgzLjQ0LDkwLjMsMCw0Ljk1LTEuMTQsMTYtMS4xNCwxNmgtMTQwLjU5YzEuOTEsNDIuMjksMzIuMDEsNjMuNjIsNjYuMjksNjMuNjJzNTcuMTUtMjIuNDcsNTcuMTUtMjIuNDdsMTUuMjQsMjcuMDVzLTI4LjU3LDI3LjQzLTc0LjY3LDI3LjQzYy02MC41NywwLTEwMi4xMS00My44MS0xMDIuMTEtMTAwLjk2LDAtNjEuMzQsNDEuNTQtMTAwLjk2LDk2LjM5LTEwMC45NlpNNDY4OC40MSwyNzg3LjExYy0xLjE1LTMzLjE1LTIxLjcyLTQ5LjE1LTQ2LjQ4LTQ5LjE1LTI4LjE5LDAtNTEuMDUsMTcuNTItNTYuMzgsNDkuMTVoMTAyLjg3WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTQ3NzEuMDksMjcxMy4yaDM1LjgxdjMzLjUyYzAsOC0uNzYsMTQuNDgtLjc2LDE0LjQ4aC43NmM4Ljc3LTI4LjIsMzEuMjQtNTAuMjksNjAuOTYtNTAuMjksNC45NiwwLDkuNTIuNzYsOS41Mi43NnYzNi41N3MtNC45NS0xLjE0LTEwLjY3LTEuMTRjLTIzLjYzLDAtNDUuMzMsMTYuNzYtNTQuMSw0NS4zNC0zLjQ0LDExLjA0LTQuNTgsMjIuODYtNC41OCwzNC42NnY3OC44N2gtMzYuOTV2LTE5Mi43OFoiIGNsYXNzPSJjbHMtMiI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Ik00OTE2LjI1LDI4NTYuMDdzMjEuNzIsMjIuNDcsNTUuMjQsMjIuNDdjMTYsMCwzMi4wMS04LjM4LDMyLjAxLTI0LDAtMzUuNDMtOTkuMDYtMjguMTktOTkuMDYtOTEuMDYsMC0zNS4wNSwzMS4yNC01NC44Niw2OS43MS01NC44Niw0Mi4yOSwwLDYyLjEsMjEuMzQsNjIuMSwyMS4zNGwtMTQuODYsMjcuODFzLTE3LjE0LTE3LjE1LTQ3LjYyLTE3LjE1Yy0xNiwwLTMxLjYxLDYuODYtMzEuNjEsMjMuNjIsMCwzNC42Nyw5OS4wNiwyNy4wNSw5OS4wNiw5MC4zLDAsMzItMjcuNDMsNTYtNjkuNzMsNTYtNDcuMjQsMC03My4xNS0yOC4xOS03My4xNS0yOC4xOWwxNy45MS0yNi4yOVoiIGNsYXNzPSJjbHMtMiI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Ik01MDg0LjY1LDI3MTMuMmgzMy45MXYxNi4zOGMwLDcuNjItLjc3LDE0LjEtLjc3LDE0LjFoLjc3czE2LjM4LTM1LjA2LDY0Ljc3LTM1LjA2YzUxLjgyLDAsODQuNTcsNDEuMTUsODQuNTcsMTAwLjk2cy0zNi45NSwxMDAuOTYtODcuMjQsMTAwLjk2Yy00Mi4yOSwwLTU5LjA2LTMxLjYyLTU5LjA2LTMxLjYyaC0uNzZzLjc2LDYuODYuNzYsMTYuNzZ2ODYuNDloLTM2Ljk1di0yNjguOThaTTUxNzQuOTQsMjg3OC45M2MzMC40NywwLDU1LjYyLTI1LjE1LDU1LjYyLTY4Ljk2cy0yMi40Ny02OC45Ni01NC40OC02OC45NmMtMjguOTYsMC01NS42MiwyMC4xOS01NS42Miw2OS4zNCwwLDM0LjI5LDE5LjA1LDY4LjU4LDU0LjQ4LDY4LjU4WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTU0MTMuODIsMjc4NS41OWg4LjM4di0zLjQzYzAtMzEuNjItMTcuOTEtNDIuMjktNDIuMjktNDIuMjktMjkuNzIsMC01My43MSwxOC42Ny01My43MSwxOC42N2wtMTUuMjQtMjcuMDVzMjcuODItMjIuODYsNzIuMDEtMjIuODZjNDguNzcsMCw3Ni4yLDI2LjY3LDc2LjIsNzUuNDR2MTIxLjkyaC0zNC4yOXYtMTguMjljMC04Ljc2Ljc3LTE1LjI0Ljc3LTE1LjI0aC0uNzdzLTE1LjYxLDM4LjA5LTYxLjcxLDM4LjA5Yy0zMy4xNSwwLTY1LjUzLTIwLjE5LTY1LjUzLTU4LjY3LDAtNjMuNjIsODMuODItNjYuMjksMTE2LjItNjYuMjlaTTUzNzEuMTYsMjg4MC44M2MzMS4yNCwwLDUxLjQzLTMyLjc2LDUxLjQzLTYxLjM0di02LjFoLTkuNTJjLTI3LjgyLDAtNzguMSwxLjktNzguMSwzNi41NywwLDE1LjYyLDEyLjE5LDMwLjg2LDM2LjE5LDMwLjg2WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTU2MDMuOTUsMjcwOC42MmM0OC4zOCwwLDcyLjM4LDI4LjIsNzIuMzgsMjguMmwtMTcuNTIsMjUuOTFzLTIwLjU4LTIyLjEtNTMuMzQtMjIuMWMtMzguODYsMC02Ny4wNSwyOC45NS02Ny4wNSw2OC41OHMyOC4xOSw2OS4zNCw2OC4yLDY5LjM0YzM1LjgxLDAsNTkuNDMtMjUuOSw1OS40My0yNS45bDE0Ljg2LDI3LjA1cy0yNi42OCwzMC44Ni03Ni45NiwzMC44NmMtNjAuNTksMC0xMDMuMjUtNDMuMDUtMTAzLjI1LTEwMC45NnM0Mi42Ni0xMDAuOTYsMTAzLjI1LTEwMC45NloiIGNsYXNzPSJjbHMtMiI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Ik01ODA1Ljg3LDI3MDguNjJjNTQuNDgsMCw4My40NCw0MC4zOSw4My40NCw5MC4zLDAsNC45NS0xLjE0LDE2LTEuMTQsMTZoLTE0MC41OWMxLjkxLDQyLjI5LDMyLjAxLDYzLjYyLDY2LjI5LDYzLjYyczU3LjE1LTIyLjQ3LDU3LjE1LTIyLjQ3bDE1LjI0LDI3LjA1cy0yOC41NywyNy40My03NC42NywyNy40M2MtNjAuNTcsMC0xMDIuMTEtNDMuODEtMTAyLjExLTEwMC45NiwwLTYxLjM0LDQxLjU0LTEwMC45Niw5Ni4zOS0xMDAuOTZaTTU4NTEuNiwyNzg3LjExYy0xLjE1LTMzLjE1LTIxLjcyLTQ5LjE1LTQ2LjQ4LTQ5LjE1LTI4LjE5LDAtNTEuMDUsMTcuNTItNTYuMzgsNDkuMTVoMTAyLjg3WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgIDwvZz4KICAgICAgPGc+CiAgICAgICAgPHBhdGggZD0iTTM4MzAuNCwzMDQyaDgyLjI5YzI4LjE5LDAsNDAuMDEsMi4yOSw1MC4yOSw2LjEsMjcuNDMsMTAuMjksNDUuMzQsMzcuMzQsNDUuMzQsNzIuNzdzLTE5LjA1LDYzLjI0LTQ4LjM5LDcyLjc2di43NnMzLjA1LDMuNDMsOCwxMi4xOWw1Ny4xNSwxMDQuMzloLTQyLjY2bC01Ni43Ny0xMDcuMDZoLTU3LjUzdjEwNy4wNmgtMzcuNzJ2LTI2OC45OFpNMzkyMi4yMSwzMTcxLjE1YzI5LjM0LDAsNDcuNjItMTguNjcsNDcuNjItNDguNzcsMC0xOS44MS03LjYyLTMzLjkxLTIxLjMzLTQxLjUyLTcuMjQtMy44MS0xNi02LjEtMzYuOTYtNi4xaC00My40M3Y5Ni4zOGg1NC4xWiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTQxNTYuOSwzMTEzLjYyYzU3LjUzLDAsMTA0LjAxLDQyLjI5LDEwNC4wMSwxMDAuNThzLTQ2LjQ3LDEwMS4zNC0xMDQuMDEsMTAxLjM0LTEwNC4wMS00Mi42Ny0xMDQuMDEtMTAxLjM0LDQ2LjQ4LTEwMC41OCwxMDQuMDEtMTAwLjU4Wk00MTU2LjksMzI4My41NGMzNi41NywwLDY2LjI5LTI4Ljk1LDY2LjI5LTY5LjM0cy0yOS43Mi02OC41OC02Ni4yOS02OC41OC02Ni4yOSwyOC41Ny02Ni4yOSw2OC41OCwzMC4xLDY5LjM0LDY2LjI5LDY5LjM0WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTQzMDcuMDIsMzI2MS4wN3MyMS43MiwyMi40Nyw1NS4yNCwyMi40N2MxNiwwLDMyLjAxLTguMzgsMzIuMDEtMjQsMC0zNS40My05OS4wNi0yOC4xOS05OS4wNi05MS4wNiwwLTM1LjA1LDMxLjI0LTU0Ljg2LDY5LjcxLTU0Ljg2LDQyLjI5LDAsNjIuMSwyMS4zNCw2Mi4xLDIxLjM0bC0xNC44NiwyNy44MXMtMTcuMTQtMTcuMTUtNDcuNjItMTcuMTVjLTE2LDAtMzEuNjEsNi44Ni0zMS42MSwyMy42MiwwLDM0LjY3LDk5LjA2LDI3LjA1LDk5LjA2LDkwLjMsMCwzMi0yNy40Myw1Ni02OS43Myw1Ni00Ny4yNCwwLTczLjE1LTI4LjE5LTczLjE1LTI4LjE5bDE3LjkxLTI2LjI5WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTQ1NTguNDgsMzExMy42MmM1NC40OCwwLDgzLjQ0LDQwLjM5LDgzLjQ0LDkwLjMsMCw0Ljk1LTEuMTQsMTYtMS4xNCwxNmgtMTQwLjU5YzEuOTEsNDIuMjksMzIuMDEsNjMuNjIsNjYuMjksNjMuNjJzNTcuMTUtMjIuNDcsNTcuMTUtMjIuNDdsMTUuMjQsMjcuMDVzLTI4LjU3LDI3LjQzLTc0LjY3LDI3LjQzYy02MC41NywwLTEwMi4xMS00My44MS0xMDIuMTEtMTAwLjk2LDAtNjEuMzQsNDEuNTQtMTAwLjk2LDk2LjM5LTEwMC45NlpNNDYwNC4yMSwzMTkyLjExYy0xLjE1LTMzLjE1LTIxLjcyLTQ5LjE1LTQ2LjQ4LTQ5LjE1LTI4LjE5LDAtNTEuMDUsMTcuNTItNTYuMzksNDkuMTVoMTAyLjg4WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTQ2ODYuODgsMzExOC4yaDM1LjgxdjI1LjUyYzAsNy42Mi0uNzYsMTQuMS0uNzYsMTQuMWguNzZjNy42My0xNi43NiwzMC40OC00NC4yLDcyLjM5LTQ0LjIsNDUuMzMsMCw2Ni4yOSwyNC43Nyw2Ni4yOSw3My45MXYxMjMuNDRoLTM2Ljk2di0xMTUuMDZjMC0yNy4wNS01LjcyLTQ4LjM5LTM2LjU3LTQ4LjM5cy01Mi45NiwxOS40My02MC45Niw0Ny4yNWMtMi4yOCw3LjYyLTMuMDUsMTYuMzgtMy4wNSwyNS45djkwLjNoLTM2Ljk1di0xOTIuNzhaIiBjbGFzcz0iY2xzLTIiPjwvcGF0aD4KICAgICAgICA8cGF0aCBkPSJNNDkxNi42MiwzMDQyaDM2Ljk1djk4LjY3YzAsOS4xNS0uNzYsMTYuMDEtLjc2LDE2LjAxaC43NmM4LjM4LTE4LjY3LDMyLjc3LTQzLjA1LDcxLjI1LTQzLjA1LDQ1LjMzLDAsNjYuMjksMjQuNzcsNjYuMjksNzMuOTF2MTIzLjQ0aC0zNi45NnYtMTE1LjA2YzAtMjcuMDUtNS43Mi00OC4zOS0zNi41Ny00OC4zOS0yOC45NiwwLTUyLjk2LDE5LjgxLTYwLjk2LDQ3LjYyLTIuMjgsNy42Mi0zLjA1LDE2LjM4LTMuMDUsMjUuNTJ2OTAuM2gtMzYuOTV2LTI2OC45OFoiIGNsYXNzPSJjbHMtMiI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Ik01MjI5LjQxLDMxMTMuNjJjNTQuNDgsMCw4My40NCw0MC4zOSw4My40NCw5MC4zLDAsNC45NS0xLjE0LDE2LTEuMTQsMTZoLTE0MC41OWMxLjkxLDQyLjI5LDMyLjAxLDYzLjYyLDY2LjI5LDYzLjYyczU3LjE1LTIyLjQ3LDU3LjE1LTIyLjQ3bDE1LjI0LDI3LjA1cy0yOC41NywyNy40My03NC42NywyNy40M2MtNjAuNTcsMC0xMDIuMTEtNDMuODEtMTAyLjExLTEwMC45NiwwLTYxLjM0LDQxLjU0LTEwMC45Niw5Ni4zOS0xMDAuOTZaTTUyNzUuMTQsMzE5Mi4xMWMtMS4xNS0zMy4xNS0yMS43Mi00OS4xNS00Ni40OC00OS4xNS0yOC4xOSwwLTUxLjA1LDE3LjUyLTU2LjM4LDQ5LjE1aDEwMi44N1oiIGNsYXNzPSJjbHMtMiI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Ik01MzU3LjQ0LDMwNDJoMzcuMzN2MzcuNzJoLTM3LjMzdi0zNy43MlpNNTM1Ny44MiwzMTE4LjJoMzYuOTV2MTkyLjc4aC0zNi45NXYtMTkyLjc4WiIgY2xhc3M9ImNscy0yIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTU0NTIuNjksMzExOC4yaDM1LjgxdjI1LjUyYzAsNy42Mi0uNzYsMTQuMS0uNzYsMTQuMWguNzZjOS4xNC0yMi40OCwzNi4xOS00NC4yLDY2LjI5LTQ0LjIsMzIuMzgsMCw1MS40MywxNC44Niw1Ny45Miw0My44MmguNzZjMTAuNjctMjMuMjQsMzcuMzMtNDMuODIsNjguNTctNDMuODIsNDMuNDMsMCw2My42MiwyNC43Nyw2My42Miw3My45MXYxMjMuNDRoLTM2Ljk1di0xMTUuNDRjMC0yNy4wNS01LjMzLTQ4LjM4LTM0LjI5LTQ4LjM4LTI3LjA1LDAtNDcuMjQsMjIuODYtNTQuMSw0OS4xNC0xLjkxLDguMDEtMi42NywxNi43Ny0yLjY3LDI2LjY3djg4LjAxaC0zNi45NnYtMTE1LjQ0YzAtMjUuMTQtMy44MS00OC4zOC0zMy41Mi00OC4zOC0yOC4xOSwwLTQ4LjAxLDIzLjI0LTU1LjI0LDUwLjY3LTEuOTEsNy42Mi0yLjI5LDE2LjM4LTIuMjksMjUuMTV2ODguMDFoLTM2Ljk1di0xOTIuNzhaIiBjbGFzcz0iY2xzLTIiPjwvcGF0aD4KICAgICAgPC9nPgogICAgPC9nPgogICAgPGc+CiAgICAgIDxwYXRoIGQ9Ik0yNTQ4LjY4LDIwMjEuNzNzNzguODUsODguMDEsMTk1LjQ0LDg4LjAxYzkwLjMsMCwxNjQuNTktNjAuNTcsMTY0LjU5LTE0Ny40NCwwLTk5LjQ0LTg4LjAxLTE0OC41OS0xODcuNDUtMTQ4LjU5aC01NmwtMjYuMjktNjAuNTcsMTc2LjAxLTIwNi44OGMyNi4yOS0zMC44Niw1MC4yOS01Mi41Nyw1MC4yOS01Mi41N3YtMi4yOXMtMjQsMy40My02OC41NywzLjQzaC0yNzMuMTd2LTk4LjI5aDQ4Mi4zM3Y3Mi4wMWwtMjE5LjQ1LDI1Mi41OWMxMDYuMywxMS40MywyMzYuNiw4MC4wMSwyMzYuNiwyMzYuNTksMCwxMzguMy0xMDguNTgsMjU5LjQ1LTI3NC4zMiwyNTkuNDVzLTI2MS43NC0xMDkuNzItMjYxLjc0LTEwOS43Mmw2MS43My04NS43MloiIGNsYXNzPSJjbHMtMiI+PC9wYXRoPgogICAgICA8Zz4KICAgICAgICA8cGF0aCBkPSJNMTY4Ni44NSwxMzk2LjUzaDExMy4xNXYzNTQuMzJoNDE4LjMzdi0zNTQuMzJoMTEzLjE1djgwNi45M2gtMTEzLjE1di0zNTQuMzJoLTQxOC4zM3YzNTQuMzJoLTExMy4xNXYtODA2LjkzWiIgY2xhc3M9ImNscy0xIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTM1NTQuNDgsMTM4Mi44MmMxOTQuMywwLDI5My43NCwxMDYuMjksMjkzLjc0LDEwNi4yOWwtNTYuMDEsODQuNThzLTkzLjcyLTg4LjAxLTIzMy4xNi04OC4wMWMtMTgwLjU4LDAtMjk4LjMxLDEzNy4xNS0yOTguMzEsMzA4LjZzMTIwLjAyLDMxOC44OCwyOTkuNDUsMzE4Ljg4YzE1Mi4wMiwwLDI0OS4xNi0xMDUuMTUsMjQ5LjE2LTEwNS4xNWw2MC41OSw4MS4xNXMtMTEwLjg2LDEyOC4wMS0zMTMuMTcsMTI4LjAxYy0yNDIuMywwLTQxMi42LTE4NS4xNi00MTIuNi00MjEuNzVzMTc2LjAxLTQxMi42LDQxMC4zMi00MTIuNloiIGNsYXNzPSJjbHMtMSI+PC9wYXRoPgogICAgICAgIDxwYXRoIGQ9Ik00MDI0LjI1LDEzOTYuNTNoMTEzLjE1djMzOS40NmgxMjAuMDJsMjAzLjQ1LTMzOS40NmgxMjQuNThsLTIzNC4zMSwzODIuODl2Mi4yOWwyNDkuMTYsNDIxLjc1aC0xMjguMDJsLTIxNC44Ny0zNzAuMzJoLTEyMC4wMnYzNzAuMzJoLTExMy4xNXYtODA2LjkzWiIgY2xhc3M9ImNscy0xIj48L3BhdGg+CiAgICAgICAgPHBhdGggZD0iTTQ3MzYuMzMsMTM5Ni41M2g0NjguNjF2OTguMjloLTM1NS40NnYyNTIuNTloMjg5LjE3djk4LjI5aC0yODkuMTd2MjU5LjQ1aDM3NC45djk4LjI5aC00ODguMDR2LTgwNi45M1oiIGNsYXNzPSJjbHMtMSI+PC9wYXRoPgogICAgICA8L2c+CiAgICA8L2c+CiAgPC9zdmc+"

_H3CKE_LOGO = f"""
<div class="logo">
  <img src="data:image/svg+xml;base64,{_H3CKE_LOGO_B64}" alt="H3cke Makerspace" style="max-width:200px;height:auto;display:block;margin:0 auto">
  <div class="logo-text">H3cke Makerspace</div>
</div>
"""

_PAYMENT_LABELS = {
    "bar": "Barzahlung",
    "karte": "Kartenzahlung",
    "wero": "Wero",
}


def laufzettel_receipt_html(
    lz, materials: list, view_url: Optional[str] = None, request=None
) -> str:
    """HTML receipt email for a paid or newly created Laufzettel."""
    date_str = lz.date.strftime("%d.%m.%Y") if lz.date else "—"
    method_label = _PAYMENT_LABELS.get(
        lz.payment_method or "", lz.payment_method or "—"
    )
    owner = lz.owner_name or "Gast"

    if not view_url:
        from backend.config import PUBLIC_BASE_URL

        if PUBLIC_BASE_URL:
            base_url = PUBLIC_BASE_URL
        elif request:
            base_url = f"{request.url.scheme}://{request.url.netloc}"
        else:
            base_url = "https://h3cke.de"
        view_url = f"{base_url}/laufzettel/view/{lz.id}"

    rows_html = ""
    total = 0.0
    for mat in materials:
        price = mat.calculated_price or 0.0
        total += price
        if mat.menge is not None and mat.unit:
            qty = f"{mat.menge} {mat.unit}"
        elif mat.menge is not None:
            qty = str(mat.menge)
        else:
            qty = "—"
        rows_html += (
            f"<tr>"
            f"<td>{mat.name or '—'}</td>"
            f"<td>{qty}</td>"
            f"<td style='text-align:right'>{price:.2f}&nbsp;€</td>"
            f"</tr>"
        )

    if not rows_html:
        rows_html = (
            "<tr><td colspan='3' style='color:#888'>Keine Materialien erfasst</td></tr>"
        )

    # Adjust content based on payment status
    if lz.payment_method:
        subject_header = "Quittung"
        intro_text = "Hier ist deine Quittung für deinen Besuch in der H3cke."
        cta_text = f"Laufzettel #{lz.id} ansehen"
    else:
        subject_header = "Laufzettel erstellt"
        intro_text = f"Hallo {owner}, danke für deinen Besuch in der H3cke! Dein Laufzettel wurde erfolgreich erstellt."
        cta_text = f"Laufzettel #{lz.id} verwalten"

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>Laufzettel #{lz.id} – H3cke</title>
<style>{_BASE_STYLE}</style></head>
<body>
{_H3CKE_LOGO}
<h1>{subject_header} – Laufzettel #{lz.id}</h1>
<p>
  {intro_text}<br>
  <strong>Datum:</strong> {date_str}<br>
  {method_label != "—" and f"<strong>Zahlungsart:</strong> {method_label}" or ""}
</p>
<table>
  <thead>
    <tr><th>Material</th><th>Menge</th><th style="text-align:right">Preis</th></tr>
  </thead>
  <tbody>
    {rows_html}
    <tr class="total-row">
      <td colspan="2">Gesamt</td>
      <td style="text-align:right'>{total:.2f}&nbsp;€</td>
    </tr>
  </tbody>
</table>

<p style="margin: 20px 0;">
  <a class="btn" href="{view_url}" style="display: block; text-align: center;">
    {cta_text}
  </a>
</p>

<p style="font-size: 0.85em; color: #666;">
  Direktlink: <a href="{view_url}" style="color: #666;">{view_url}</a>
</p>

<p class="footer">H3cke Makerspace &middot; Vielen Dank für deinen Besuch!</p>
</body>
</html>"""


def easyverein_signup_html(name: str, signup_url: str) -> str:
    """HTML email inviting a guest to sign up as an easyVerein member."""
    if signup_url:
        cta_html = (
            f'<p><a class="btn" href="{signup_url}">Jetzt Mitglied werden</a></p>'
            f'<p style="font-size:0.9em">Direktlink: <a href="{signup_url}">{signup_url}</a></p>'
        )
    else:
        cta_html = (
            "<p>Sprich uns vor Ort an oder schreib uns eine E-Mail,"
            " um die Mitgliedschaft zu beantragen.</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>Willkommen in der H3cke!</title>
<style>{_BASE_STYLE}</style></head>
<body>
{_H3CKE_LOGO}
<h1>Willkommen in der H3cke! Jetzt Mitglied werden</h1>
<p>Hallo {name},</p>
<p>danke für deinen Besuch in der H3cke! Wir freuen uns, dass du unsere Maschinen und
Materialien genutzt hast.</p>
<p>Als <strong>Mitglied</strong> profitierst du von:</p>
<ul>
  <li>Dein digitaler Laufzettel mit deiner persönlichen RFID-Karte</li>
  <li>Nutzung aller Maschinen und Werkzeuge</li>
  <li>Einer aktiven Community von Makern</li>
</ul>
<p>Die Mitgliedschaft wird über <strong>easyVerein</strong> verwaltet:</p>
{cta_html}
<p class="footer">
  H3cke Makerspace &middot; Diese E-Mail wurde automatisch nach deinem Besuch verschickt.
</p>
</body>
</html>"""
