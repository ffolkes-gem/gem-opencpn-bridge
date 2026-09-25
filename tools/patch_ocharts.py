chart = chart.replace('GEM +29', 'GEM +30')
chart = chart.replace('GEMBUILD +30 peer-chart geographic coordinates active', 'GEMBUILD +30 production candidate output active')


# +32 standard full-GPX route handoff with 100 km route guard.
chart = chart.replace('gemDir + wxFILE_SEP_PATH + _T("gem-route-query.json")',
                      'gemDir + wxFILE_SEP_PATH + _T("gem-route.gpx")')

old = r'''            // +16: bounded multi-waypoint parser. Accept 2..32
            // {"lat":..., "lon":...} points from the GEM route file.
            double routeLat[32] = {0.0};
            double routeLon[32] = {0.0};
            int routePointCount = 0;

            size_t scanPos = 0;

            while( routePointCount < 32 ) {
                int latPos = routeText.find(_T("\"lat\""), scanPos);
                if( latPos == wxNOT_FOUND ) break;

                int latColon = routeText.find(_T(":"), latPos);
                int lonPos = routeText.find(_T("\"lon\""), latColon);
                if( latColon == wxNOT_FOUND || lonPos == wxNOT_FOUND ) break;

                int lonColon = routeText.find(_T(":"), lonPos);
                if( lonColon == wxNOT_FOUND ) break;

                wxString latTail = routeText.Mid(latColon + 1);
                wxString lonTail = routeText.Mid(lonColon + 1);

                double la = 0.0, lo = 0.0;

                if( !latTail.ToDouble(&la) ) {
                    wxString token = latTail.BeforeFirst(',');
                    token.Trim(true).Trim(false);
                    if( !token.ToDouble(&la) ) break;
                }

                wxString lonToken = lonTail.BeforeFirst('}');
                lonToken.Trim(true).Trim(false);
                if( !lonToken.ToDouble(&lo) ) {
                    lonToken = lonTail.BeforeFirst(',');
                    lonToken.Trim(true).Trim(false);
                    if( !lonToken.ToDouble(&lo) ) break;
                }

                routeLat[routePointCount] = la;
                routeLon[routePointCount] = lo;
                routePointCount++;
                scanPos = lonColon + 1;
            }'''
new = r'''            // +31: standard GPX handoff parser. Reads rtept/trkpt/wpt
            // coordinates in file order. 512 is a defensive point ceiling only.
            double routeLat[512] = {0.0};
            double routeLon[512] = {0.0};
            int routePointCount = 0;
            size_t scanPos = 0;

            while( routePointCount < 512 ) {
                int rtePos = routeText.find(_T("<rtept"), scanPos);
                int trkPos = routeText.find(_T("<trkpt"), scanPos);
                int wptPos = routeText.find(_T("<wpt"), scanPos);
                int pointPos = wxNOT_FOUND;
                if( rtePos != wxNOT_FOUND ) pointPos = rtePos;
                if( trkPos != wxNOT_FOUND && (pointPos == wxNOT_FOUND || trkPos < pointPos) ) pointPos = trkPos;
                if( wptPos != wxNOT_FOUND && (pointPos == wxNOT_FOUND || wptPos < pointPos) ) pointPos = wptPos;
                if( pointPos == wxNOT_FOUND ) break;

                int tagEnd = routeText.find(_T(">"), pointPos);
                if( tagEnd == wxNOT_FOUND ) break;
                wxString tag = routeText.Mid(pointPos, tagEnd - pointPos + 1);
                int latKey = tag.find(_T("lat=\""));
                int lonKey = tag.find(_T("lon=\""));
                if( latKey == wxNOT_FOUND || lonKey == wxNOT_FOUND ) {
                    scanPos = tagEnd + 1;
                    continue;
                }

                int latStart = latKey + 5;
                int lonStart = lonKey + 5;
                int latEnd = tag.find(_T("\""), latStart);
                int lonEnd = tag.find(_T("\""), lonStart);
                if( latEnd == wxNOT_FOUND || lonEnd == wxNOT_FOUND ) {
                    scanPos = tagEnd + 1;
                    continue;
                }

                wxString latToken = tag.Mid(latStart, latEnd - latStart);
                wxString lonToken = tag.Mid(lonStart, lonEnd - lonStart);
                double la = 0.0, lo = 0.0;
                if( latToken.ToDouble(&la) && lonToken.ToDouble(&lo) &&
                    la >= -90.0 && la <= 90.0 && lo >= -180.0 && lo <= 180.0 ) {
                    routeLat[routePointCount] = la;
                    routeLon[routePointCount] = lo;
                    routePointCount++;
                }
                scanPos = tagEnd + 1;
            }

            wxLogMessage(_T("GEMGPX +32 READ points=%d path=%s"),
                         routePointCount, routeInputPath.c_str());'''
if old not in chart: raise RuntimeError('+31 GPX parser anchor not found')
chart = chart.replace(old, new, 1)

old = '                if( routeValid && routeLength <= 30000.0 ) {'
new = '''                if( routeValid && routeLength <= 100000.0 ) {
                    wxLogMessage(_T("GEMROUTE +32 FULL ROUTE length=%.1f m points=%d"),
                                 routeLength, routePointCount);'''
if old not in chart: raise RuntimeError('+31 route-length gate anchor not found')
chart = chart.replace(old, new, 1)

chart = chart.replace('gem-route-query.json must contain 2 to 32 ',
                      'gem-route.gpx must contain at least 2 valid ')
chart = chart.replace('lat/lon route points', 'GPX route/track points')
chart = chart.replace('route length %.1f m outside diagnostic limit',
                      'invalid route geometry, length %.1f m')

# Add GPX provenance to v3 output.
old = r'''                    candidatesJson << _T("  \"scanner_version\": \"GEM +30\",\n");'''
if old in chart:
    new = old + r'''
                    candidatesJson << _T("  \"route_input\": \"gem-route.gpx\",\n");
                    candidatesJson << wxString::Format(_T("  \"input_point_count\": %d,\n"), routePointCount);'''
    chart = chart.replace(old, new, 1)

for a,b in [('GEMPROX +30','GEMPROX +32'),('GEMPOINT +30','GEMPOINT +32'),
            ('GEMROUTE +30','GEMROUTE +32'),('GEMVIEW +30','GEMVIEW +32'),
            ('GEMDIAG +30','GEMDIAG +32'),('GEMCANDIDATES +30','GEMCANDIDATES +32'),
            ('GEM +30','GEM +32')]:
    chart = chart.replace(a,b)
chart = chart.replace('GEMBUILD +32 production candidate output active',
                      'GEMBUILD +32 full GPX route scalability test active')

chart_path.write_text(chart, encoding="utf-8")

print("Patched", chart_path)
print("GEM +29: peer-chart PI_S57Obj geographic coordinates used directly")
print("GEM +29: point-object identity qualified by geographic position")
print("GEM +11: +9 selected-object export retained")
print("GEM +11: +10 corridor diagnostic retained")
print("GEM +32: standard gem-route.gpx input, up to 512 GPX points, 100 km route-length guard")
print("GEM +18: normalized/raw navigation candidates -> gem-route-candidates-v2.json")
