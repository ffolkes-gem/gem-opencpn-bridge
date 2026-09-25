from pathlib import Path

chart_path = Path("ocharts/src/eSENCChart.cpp")
chart = chart_path.read_text(encoding="utf-8")


def replace_once(src, old, new, label):
    if old not in src:
        raise SystemExit(f"Patch anchor not found: {label}. Upstream source changed.")
    return src.replace(old, new, 1)


# ------------------------------------------------------------
# GEM +14 cumulative
# Keeps +9 selected-object JSON intact.
# Adds a deliberately small 5x5 diagnostic grid around the
# user's normal Object Query click and writes a deduplicated
# gem-corridor-test.json.
# ------------------------------------------------------------

chart = replace_once(
    chart,
    """#include <unordered_map>
""",
    """#include <unordered_map>
#include <wx/ffile.h>
#include <wx/stdpaths.h>
#include <wx/filename.h>
#include <map>
""",
    "includes"
)

# JSON escaping helper and copied query state.
chart = replace_once(
    chart,
    """ListOfPI_S57Obj *eSENCChart::GetObjRuleListAtLatLon(float lat, float lon, float select_radius,
                                                    PlugIn_ViewPort *VPoint)

{
""",
    r"""static wxString GEMJsonEscape(const wxString &input)
{
    wxString s = input;
    s.Replace(_T("\\"), _T("\\\\"));
    s.Replace(_T("\""), _T("\\\""));
    s.Replace(_T("\r"), _T("\\r"));
    s.Replace(_T("\n"), _T("\\n"));
    s.Replace(_T("\t"), _T("\\t"));
    return s;
}

// +10 diagnostic state.  The viewport is COPIED, not retained as a pointer.
static bool g_gemHaveQuery = false;
static bool g_gemInternalScan = false;
static float g_gemQueryLat = 0.0f;
static float g_gemQueryLon = 0.0f;
static float g_gemQueryRadius = 0.0f;
static PlugIn_ViewPort g_gemQueryVP;


ListOfPI_S57Obj *eSENCChart::GetObjRuleListAtLatLon(float lat, float lon, float select_radius,
                                                    PlugIn_ViewPort *VPoint)

{
    // Only remember the real OpenCPN query.  Internal +10 sample calls must
    // not replace the trigger coordinate/viewport.
    if( !g_gemInternalScan && VPoint ) {
        g_gemQueryLat = lat;
        g_gemQueryLon = lon;
        g_gemQueryRadius = select_radius;
        g_gemQueryVP = *VPoint;
        g_gemHaveQuery = true;
    }
""",
    "query state capture"
)

# +9 marker and existing selected-object exporter setup.
chart = replace_once(
    chart,
    """wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
""",
    r"""wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
    wxLogMessage(
        _T("GEMPROBE +10 ENTER objects=%lu"),
        (unsigned long)obj_list->GetCount()
    );
""",
    "CreateObjDescriptions marker"
)

chart = replace_once(
    chart,
    """    PI_S57Light* curLight = NULL;

    for( ListOfPI_S57Obj::Node *node = obj_list->GetLast(); node; node = node->GetPrevious() ) {
""",
    r"""    PI_S57Light* curLight = NULL;

    // Existing +9 complete Object Query document.
    wxString gemJson;
    gemJson << _T("{\n");
    gemJson << _T("  \"gem_format\": \"navigation-object-selection-v1\",\n");
    gemJson << _T("  \"objects\": [\n");

    bool gemFirstObject = true;
    unsigned long gemExportedObjects = 0;

    for( ListOfPI_S57Obj::Node *node = obj_list->GetLast(); node; node = node->GetPrevious() ) {
""",
    "selected JSON start"
)

chart = replace_once(
    chart,
    """        className = wxString( current->FeatureName, wxConvUTF8 );

        // Lights get grouped together to make display look nicer.
""",
    r"""        className = wxString( current->FeatureName, wxConvUTF8 );

        double gemLat = 0.0;
        double gemLon = 0.0;
        bool gemHasPosition = false;
        wxString gemAttributes;
        bool gemFirstAttribute = true;

        // Lights get grouped together to make display look nicer.
""",
    "per-object state"
)

chart = replace_once(
    chart,
    """                if( lon > 180.0 ) lon -= 360.;

                positionString.Clear();
""",
    """                if( lon > 180.0 ) lon -= 360.;

                gemLat = lat;
                gemLon = lon;
                gemHasPosition = true;

                positionString.Clear();
""",
    "position capture"
)

chart = replace_once(
    chart,
    """                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( isLight ) {
""",
    r"""                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( !gemFirstAttribute )
                        gemAttributes << _T(",\n");

                    gemAttributes << _T("        \"")
                                  << GEMJsonEscape(curAttrName)
                                  << _T("\": \"")
                                  << GEMJsonEscape(value)
                                  << _T("\"");
                    gemFirstAttribute = false;

                    if( isLight ) {
""",
    "attribute capture"
)

# Close +9 and add +10 diagnostic immediately after normal object loop.
chart = replace_once(
    chart,
    """            }
    } // Object for loop

    // Add the additional info files
""",
    r"""            }

        if( !gemFirstObject )
            gemJson << _T(",\n");

        gemJson << _T("    {\n");
        gemJson << _T("      \"feature\": \"")
                << GEMJsonEscape(className)
                << _T("\",\n");
        gemJson << wxString::Format(_T("      \"index\": %d"), current->Index);

        if( gemHasPosition ) {
            gemJson << wxString::Format(
                _T(",\n      \"latitude\": %.8f,\n      \"longitude\": %.8f"),
                gemLat, gemLon
            );
        }

        gemJson << _T(",\n      \"attributes\": {");
        if( !gemFirstAttribute )
            gemJson << _T("\n") << gemAttributes << _T("\n      ");
        gemJson << _T("}\n");
        gemJson << _T("    }");

        gemFirstObject = false;
        gemExportedObjects++;

    } // Object for loop

    gemJson << _T("\n  ],\n");
    gemJson << wxString::Format(_T("  \"object_count\": %lu\n"), gemExportedObjects);
    gemJson << _T("}\n");

    wxString gemDir = wxStandardPaths::Get().GetUserDataDir();
    if( !wxDirExists(gemDir) )
        wxFileName::Mkdir(gemDir, wxS_DIR_DEFAULT, wxPATH_MKDIR_FULL);

    wxString gemPath = gemDir + wxFILE_SEP_PATH + _T("gem-selected-object.json");
    wxFFile gemFile;
    if( gemFile.Open(gemPath, _T("wb")) ) {
        bool ok = gemFile.Write(gemJson, wxConvUTF8);
        gemFile.Close();
        wxLogMessage(
            ok ? _T("GEMEXPORT +10 SELECTED WRITE OK objects=%lu path=%s")
               : _T("GEMEXPORT +10 SELECTED WRITE FAILED objects=%lu path=%s"),
            gemExportedObjects, gemPath.c_str()
        );
    }

    // --------------------------------------------------------
    // +10 SMALL DIAGNOSTIC GRID
    // 5x5 points centred on the user's Object Query.
    // Approx 50 m spacing N/S and E/W.
    // This is intentionally a local proof, not a chart sweep.
    // --------------------------------------------------------
    if( g_gemHaveQuery ) {
        struct GEMHit {
            wxString feature;
            int index;
            double lat;
            double lon;
            bool hasPosition;
            unsigned long hits;
        };

        std::map<wxString, GEMHit> gemHits;

        const double metresPerDegLat = 111320.0;
        const double pi = 3.14159265358979323846;
        const double cosLat = cos(((double)g_gemQueryLat) * pi / 180.0);
        const double metresPerDegLon =
            (fabs(cosLat) > 0.01) ? (111320.0 * cosLat) : 111320.0;
        const double spacingM = 50.0;

        unsigned long sampleCount = 0;
        g_gemInternalScan = true;

        for( int row = -2; row <= 2; ++row ) {
            for( int col = -2; col <= 2; ++col ) {
                const float sampleLat =
                    (float)(g_gemQueryLat + (row * spacingM / metresPerDegLat));
                const float sampleLon =
                    (float)(g_gemQueryLon + (col * spacingM / metresPerDegLon));

                ListOfPI_S57Obj *sampleObjects =
                    GetObjRuleListAtLatLon(
                        sampleLat,
                        sampleLon,
                        g_gemQueryRadius,
                        &g_gemQueryVP
                    );

                sampleCount++;

                if( sampleObjects ) {
                    for( ListOfPI_S57Obj::Node *gn = sampleObjects->GetFirst();
                         gn; gn = gn->GetNext() ) {
                        PI_S57Obj *go = gn->GetData();
                        wxString feature(go->FeatureName, wxConvUTF8);
                        wxString key = feature +
                            wxString::Format(_T(":%d"), go->Index);

                        std::map<wxString, GEMHit>::iterator it = gemHits.find(key);
                        if( it == gemHits.end() ) {
                            GEMHit hit;
                            hit.feature = feature;
                            hit.index = go->Index;
                            hit.lat = 0.0;
                            hit.lon = 0.0;
                            hit.hasPosition = false;
                            hit.hits = 1;

                            if( go->npt == 1 ) {
                                double olon, olat;
                                fromSM_Plugin(
                                    (go->x * go->x_rate) + go->x_origin,
                                    (go->y * go->y_rate) + go->y_origin,
                                    m_ref_lat, m_ref_lon,
                                    &olat, &olon
                                );
                                if( olon > 180.0 ) olon -= 360.0;
                                hit.lat = olat;
                                hit.lon = olon;
                                hit.hasPosition = true;
                            }
                            gemHits[key] = hit;
                        }
                        else {
                            it->second.hits++;
                        }
                    }

                    // GetObjRuleListAtLatLon() sets DeleteContents(true).
                    delete sampleObjects;
                }
            }
        }

        g_gemInternalScan = false;

        wxString corridor;
        corridor << _T("{\n");
        corridor << _T("  \"gem_format\": \"corridor-query-test-v1\",\n");
        corridor << wxString::Format(
            _T("  \"trigger\": {\"latitude\": %.8f, \"longitude\": %.8f},\n"),
            (double)g_gemQueryLat, (double)g_gemQueryLon
        );
        corridor << wxString::Format(
            _T("  \"grid\": {\"rows\": 5, \"columns\": 5, \"spacing_metres\": 50, \"sample_count\": %lu},\n"),
            sampleCount
        );
        corridor << _T("  \"objects\": [\n");

        bool firstHit = true;
        for( std::map<wxString, GEMHit>::const_iterator it = gemHits.begin();
             it != gemHits.end(); ++it ) {
            const GEMHit &h = it->second;
            if( !firstHit ) corridor << _T(",\n");

            corridor << _T("    {\"feature\": \"")
                     << GEMJsonEscape(h.feature)
                     << _T("\", \"index\": ")
                     << wxString::Format(_T("%d"), h.index);

            if( h.hasPosition ) {
                corridor << wxString::Format(
                    _T(", \"latitude\": %.8f, \"longitude\": %.8f"),
                    h.lat, h.lon
                );
            }

            corridor << wxString::Format(
                _T(", \"hits\": %lu}"),
                h.hits
            );
            firstHit = false;
        }

        corridor << _T("\n  ],\n");
        corridor << wxString::Format(
            _T("  \"object_count\": %lu\n"),
            (unsigned long)gemHits.size()
        );
        corridor << _T("}\n");

        wxString corridorPath =
            gemDir + wxFILE_SEP_PATH + _T("gem-corridor-test.json");

        wxFFile corridorFile;
        if( corridorFile.Open(corridorPath, _T("wb")) ) {
            bool ok = corridorFile.Write(corridor, wxConvUTF8);
            corridorFile.Close();
            wxLogMessage(
                ok ? _T("GEMCORRIDOR +10 WRITE OK objects=%lu samples=%lu path=%s")
                   : _T("GEMCORRIDOR +10 WRITE FAILED objects=%lu samples=%lu path=%s"),
                (unsigned long)gemHits.size(),
                sampleCount,
                corridorPath.c_str()
            );
        }
    }

    // --------------------------------------------------------
    // +11 ROUTE-SHAPED DIAGNOSTIC
    //
    // Reads:
    //   <OpenCPN user data>/gem-route-query.json
    //
    // Hard limits:
    //   2 to 32 route points
    //   maximum total route length 30000 m
    //   100 m along-track spacing
    //   cross-track offsets -50 / 0 / +50 m
    //
    // Writes:
    //   <OpenCPN user data>/gem-route-test.json
    //
    // Triggered only when CreateObjDescriptions() is reached by a
    // normal Object Query. This remains a deliberately bounded proof.
    // --------------------------------------------------------

    {
        wxString routeInputPath =
            gemDir + wxFILE_SEP_PATH + _T("gem-route-query.json");

        if( wxFileExists(routeInputPath) ) {

            wxFFile routeInput(routeInputPath, _T("rb"));
            wxString routeText;

            if( routeInput.IsOpened() ) {
                routeInput.ReadAll(&routeText, wxConvUTF8);
                routeInput.Close();
            }

            // +16: bounded multi-waypoint parser. Accept 2..32
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
            }

            if( routePointCount >= 2 ) {

                const double pi11 = 3.14159265358979323846;
                const double metresPerDegLat11 = 111320.0;
                const double alongSpacing = 100.0;
                const double crossOffsets[3] = {-50.0, 0.0, 50.0};

                // Validate and total every leg before scanning.
                double routeLength = 0.0;
                bool routeValid = true;

                for( int leg = 0; leg < routePointCount - 1; ++leg ) {
                    const double meanLat =
                        (routeLat[leg] + routeLat[leg + 1]) * 0.5;
                    const double metresPerDegLon11 =
                        111320.0 * cos(meanLat * pi11 / 180.0);
                    const double dNorth =
                        (routeLat[leg + 1] - routeLat[leg]) *
                        metresPerDegLat11;
                    const double dEast =
                        (routeLon[leg + 1] - routeLon[leg]) *
                        metresPerDegLon11;
                    const double legLength =
                        sqrt((dNorth * dNorth) + (dEast * dEast));

                    if( legLength <= 0.1 )
                        continue;
                    routeLength += legLength;
                }

                if( routeValid && routeLength <= 100000.0 ) {
                    wxLogMessage(_T("GEMROUTE +32 FULL ROUTE length=%.1f m points=%d"),
                                 routeLength, routePointCount);

                    struct GEMRouteHit {
                        wxString feature;
                        int index;
                        double lat;
                        double lon;
                        bool hasPosition;
                        unsigned long hits;
                        bool enriched;
                    };

                    std::map<wxString, GEMRouteHit> routeHits;

                    struct GEMCandidate {
                        wxString primaryFeature;
                        int primaryIndex;
                        double lat;
                        double lon;
                        wxString name;
                        wxString shape;
                        wxString category;
                        wxString colour;
                        wxString information;
                        wxString sourceDate;
                        wxString sourceIndication;
                        wxArrayString componentFeatures;
                        wxArrayInt componentIndexes;
                        wxArrayString lightColours;
                        wxArrayString lightCharacters;
                        wxArrayString lightGroups;
                        wxArrayString lightPeriods;

                        // +33B: preserve extended S-57 LIGHTS semantics.
                        wxArrayString lightSector1;
                        wxArrayString lightSector2;
                        wxArrayString lightCategories;
                        wxArrayString lightExhibitions;
                        wxArrayString lightHeights;
                        wxArrayString lightNominalRanges;
                        wxArrayString lightNames;
                        };

                    std::map<wxString, GEMCandidate> gemCandidates;

                    // +33A.1: candidate coordinate -> charts which actually
                    // supplied an object at that exact physical position.
                    std::map<wxString, wxArrayString> gemCandidateChartSources;

                    unsigned long routeSamples = 0;

                    // +17 diagnostic: count returned objects in five route bands.
                    unsigned long gemDiagQueries[5] = {0,0,0,0,0};
                    unsigned long gemDiagObjects[5] = {0,0,0,0,0};

                    g_gemInternalScan = true;

                    // +16 first pass: scan every route leg using the proven
                    // +15 translated viewport. Shared waypoint endpoints are
                    // harmless because routeHits deduplicates feature:index.
                    for( int leg = 0; leg < routePointCount - 1; ++leg ) {

                        const double meanLat =
                            (routeLat[leg] + routeLat[leg + 1]) * 0.5;
                        const double metresPerDegLon11 =
                            111320.0 * cos(meanLat * pi11 / 180.0);
                        const double dNorth =
                            (routeLat[leg + 1] - routeLat[leg]) *
                            metresPerDegLat11;
                        const double dEast =
                            (routeLon[leg + 1] - routeLon[leg]) *
                            metresPerDegLon11;
                        const double legLength =
                            sqrt((dNorth * dNorth) + (dEast * dEast));
                        if( legLength <= 0.1 )
                            continue;
                        const double uEast = dEast / legLength;
                        const double uNorth = dNorth / legLength;
                        const double pEast = -uNorth;
                        const double pNorth = uEast;

                        int alongSteps =
                            (int)ceil(legLength / alongSpacing);
                        if( alongSteps < 1 ) alongSteps = 1;

                        for( int step = 0; step <= alongSteps; ++step ) {
                            double along =
                                (step == alongSteps)
                                    ? legLength
                                    : step * alongSpacing;
                            if( along > legLength ) along = legLength;

                            const double baseEast = uEast * along;
                            const double baseNorth = uNorth * along;

                            for( int ci = 0; ci < 3; ++ci ) {
                                const double sampleEast =
                                    baseEast + (pEast * crossOffsets[ci]);
                                const double sampleNorth =
                                    baseNorth + (pNorth * crossOffsets[ci]);

                                const float sampleLat =
                                    (float)(routeLat[leg] +
                                        sampleNorth / metresPerDegLat11);
                                const float sampleLon =
                                    (float)(routeLon[leg] +
                                        sampleEast / metresPerDegLon11);

                                PlugIn_ViewPort routeVP = g_gemQueryVP;
                                const double routeDLat =
                                    sampleLat - routeVP.clat;
                                const double routeDLon =
                                    sampleLon - routeVP.clon;
                                routeVP.clat = sampleLat;
                                routeVP.clon = sampleLon;
                                routeVP.lat_min += routeDLat;
                                routeVP.lat_max += routeDLat;
                                routeVP.lon_min += routeDLon;
                                routeVP.lon_max += routeDLon;

                                ListOfPI_S57Obj *routeObjects =
                                    GetObjRuleListAtLatLon(
                                        sampleLat, sampleLon,
                                        g_gemQueryRadius, &routeVP);

                                routeSamples++;

                                // +17: assign each query to one of five broad
                                // route-position bands. This changes no selection logic.
                                int gemDiagBand = (int)((routeSamples - 1) * 5 / 924);
                                if( gemDiagBand < 0 ) gemDiagBand = 0;
                                if( gemDiagBand > 4 ) gemDiagBand = 4;
                                gemDiagQueries[gemDiagBand]++;
                                if( routeObjects )
                                    gemDiagObjects[gemDiagBand] +=
                                        (unsigned long)routeObjects->GetCount();

                                if( routeObjects ) {
                                    for(
                                        ListOfPI_S57Obj::Node *rn =
                                            routeObjects->GetFirst();
                                        rn;
                                        rn = rn->GetNext()
                                    ) {
                                        PI_S57Obj *ro = rn->GetData();
                                        wxString feature(
                                            ro->FeatureName, wxConvUTF8);
                                        wxString key =
                                            feature + wxString::Format(
                                                _T(":%d"), ro->Index);

                                        std::map<wxString, GEMRouteHit>::iterator
                                            hitIt = routeHits.find(key);

                                        if( hitIt == routeHits.end() ) {
                                            GEMRouteHit h;
                                            h.feature = feature;
                                            h.index = ro->Index;
                                            h.lat = 0.0;
                                            h.lon = 0.0;
                                            h.hasPosition = false;
                                            h.hits = 1;
                                            h.enriched = false;

                                            if( ro->npt == 1 ) {
                                                double olon, olat;
                                                fromSM_Plugin(
                                                    (ro->x * ro->x_rate) +
                                                        ro->x_origin,
                                                    (ro->y * ro->y_rate) +
                                                        ro->y_origin,
                                                    m_ref_lat, m_ref_lon,
                                                    &olat, &olon);
                                                if( olon > 180.0 )
                                                    olon -= 360.0;
                                                h.lat = olat;
                                                h.lon = olon;
                                                h.hasPosition = true;
                                            }
                                            routeHits[key] = h;
                                        }
                                        else {
                                            hitIt->second.hits++;
                                        }
                                    }
                                    delete routeObjects;
                                }
                            }
                        }
                    }

                    // Second pass: exact-position enrichment for point
                    // navigation marks discovered by the corridor.
                    //
                    // Snapshot the positions first because enrichment may
                    // add new objects to routeHits.
                    struct GEMEnrichPoint {
                        double lat;
                        double lon;
                    };

                    std::vector<GEMEnrichPoint> enrichPoints;

                    for(
                        std::map<wxString, GEMRouteHit>::const_iterator it =
                            routeHits.begin();
                        it != routeHits.end();
                        ++it
                    ) {
                        const GEMRouteHit &h = it->second;

                        bool primary =
                            h.feature == _T("BOYLAT") ||
                            h.feature == _T("BOYCAR") ||
                            h.feature == _T("BOYSAW") ||
                            h.feature == _T("BOYISD") ||
                            h.feature == _T("BOYSPP") ||
                            h.feature == _T("BCNLAT") ||
                            h.feature == _T("BCNCAR") ||
                            h.feature == _T("BCNSAW") ||
                            h.feature == _T("BCNSPP");

                        if( primary && h.hasPosition ) {
                            GEMEnrichPoint ep;
                            ep.lat = h.lat;
                            ep.lon = h.lon;
                            enrichPoints.push_back(ep);
                        }
                    }

                    unsigned long enrichmentQueries = 0;

                    for(
                        size_t ei = 0;
                        ei < enrichPoints.size();
                        ++ei
                    ) {
                        // +14: centre a copied viewport on the discovered
                        // mark before the exact-position component query.
                        PlugIn_ViewPort enrichVP = g_gemQueryVP;
                        const double enrichDLat =
                            enrichPoints[ei].lat - enrichVP.clat;
                        const double enrichDLon =
                            enrichPoints[ei].lon - enrichVP.clon;
                        enrichVP.clat = enrichPoints[ei].lat;
                        enrichVP.clon = enrichPoints[ei].lon;
                        enrichVP.lat_min += enrichDLat;
                        enrichVP.lat_max += enrichDLat;
                        enrichVP.lon_min += enrichDLon;
                        enrichVP.lon_max += enrichDLon;

                        ListOfPI_S57Obj *exactObjects =
                            GetObjRuleListAtLatLon(
                                (float)enrichPoints[ei].lat,
                                (float)enrichPoints[ei].lon,
                                g_gemQueryRadius,
                                &enrichVP
                            );

                        enrichmentQueries++;

                        if( exactObjects ) {

                            // Build one logical GEM candidate for the primary
                            // buoy/beacon which caused this enrichment query.
                            wxString candidateKey = wxString::Format(
                                _T("%.7f:%.7f"),
                                enrichPoints[ei].lat,
                                enrichPoints[ei].lon
                            );

                            GEMCandidate candidate;
                            candidate.primaryFeature = _T("");
                            candidate.primaryIndex = -1;
                            candidate.lat = enrichPoints[ei].lat;
                            candidate.lon = enrichPoints[ei].lon;

                            for(
                                ListOfPI_S57Obj::Node *en =
                                    exactObjects->GetFirst();
                                en;
                                en = en->GetNext()
                            ) {
                                PI_S57Obj *eo = en->GetData();

                                wxString feature(
                                    eo->FeatureName,
                                    wxConvUTF8
                                );

                                wxString key =
                                    feature +
                                    wxString::Format(
                                        _T(":%d"),
                                        eo->Index
                                    );

                                // Only components at the exact primary-mark
                                // position belong to the logical candidate.
                                bool samePosition = false;
                                double componentLat = 0.0;
                                double componentLon = 0.0;

                                if( eo->npt == 1 ) {
                                    fromSM_Plugin(
                                        (eo->x * eo->x_rate) + eo->x_origin,
                                        (eo->y * eo->y_rate) + eo->y_origin,
                                        m_ref_lat,
                                        m_ref_lon,
                                        &componentLat,
                                        &componentLon
                                    );

                                    if( componentLon > 180.0 )
                                        componentLon -= 360.0;

                                    const double dLat =
                                        fabs(componentLat - enrichPoints[ei].lat);
                                    const double dLon =
                                        fabs(componentLon - enrichPoints[ei].lon);

                                    samePosition =
                                        dLat < 0.000002 &&
                                        dLon < 0.000002;
                                }
                                  
                                if( samePosition ) {
                                    // +33A: chart-local object indexes are not stable
                                    // across overlapping ENC cells. At this exact
                                    // physical position, treat the same S-57 feature
                                    // class as one logical component.
                                    bool componentAlreadyAdded = false;

                                    for( size_t ci = 0;
                                         ci < candidate.componentFeatures.GetCount();
                                         ++ci ) {
                                        if( candidate.componentFeatures[ci] == feature ) {
                                            componentAlreadyAdded = true;
                                            break;
                                        }
                                    }

                                    if( !componentAlreadyAdded ) {
                                        candidate.componentFeatures.Add(feature);
                                        candidate.componentIndexes.Add(eo->Index);
                                    }

                                    bool isPrimary =
                                        feature == _T("BOYLAT") ||
                                        feature == _T("BOYCAR") ||
                                        feature == _T("BOYSAW") ||
                                        feature == _T("BOYISD") ||
                                        feature == _T("BOYSPP") ||
                                        feature == _T("BCNLAT") ||
                                        feature == _T("BCNCAR") ||
                                        feature == _T("BCNSAW") ||
                                        feature == _T("BCNSPP");

                                    if( isPrimary ) {
                                        candidate.primaryFeature = feature;
                                        candidate.primaryIndex = eo->Index;
                                    }

                                    wxString lightColour;
                                    wxString lightCharacter;
                                    wxString lightGroup;
                                    wxString lightPeriod;
                                    wxString lightSector1;
                                    wxString lightSector2;
                                    wxString lightCategory;
                                    wxString lightExhibition;
                                    wxString lightHeight;
                                    wxString lightNominalRange;
                                    wxString lightName;

                                    for( int ai = 0; ai < eo->n_attr; ++ai ) {
                                        wxString attrName(
                                            eo->att_array + (ai * 6),
                                            wxConvUTF8,
                                            6
                                        );

                                        wxString attrValue =
                                            GetObjectAttributeValueAsString(
                                                eo,
                                                ai,
                                                attrName
                                            );

                                        attrName.Trim(true).Trim(false);

                                        if( isPrimary ) {
                                            if( attrName == _T("OBJNAM") )
                                                candidate.name = attrValue;
                                            else if( attrName == _T("BOYSHP") ||
                                                     attrName == _T("BCNSHP") )
                                                candidate.shape = attrValue;
                                            else if( attrName == _T("CATLAM") ||
                                                     attrName == _T("CATCAM") ||
                                                     attrName == _T("CATSPM") )
                                                candidate.category = attrValue;
                                            else if( attrName == _T("COLOUR") )
                                                candidate.colour = attrValue;
                                            else if( attrName == _T("INFORM") )
                                                candidate.information = attrValue;
                                            else if( attrName == _T("SORDAT") )
                                                candidate.sourceDate = attrValue;
                                            else if( attrName == _T("SORIND") )
                                                candidate.sourceIndication = attrValue;
                                        }

                                        if( feature == _T("LIGHTS") ) {
                                            if( attrName == _T("COLOUR") )
                                                lightColour = attrValue;
                                            else if( attrName == _T("LITCHR") )
                                                lightCharacter = attrValue;
                                            else if( attrName == _T("SIGGRP") )
                                                lightGroup = attrValue;
                                            else if( attrName == _T("SIGPER") )
                                                lightPeriod = attrValue;
                                            else if( attrName == _T("SECTR1") )
                                                lightSector1 = attrValue;
                                            else if( attrName == _T("SECTR2") )
                                                lightSector2 = attrValue;
                                            else if( attrName == _T("CATLIT") )
                                                lightCategory = attrValue;
                                            else if( attrName == _T("EXCLIT") )
                                                lightExhibition = attrValue;
                                            else if( attrName == _T("HEIGHT") )
                                                lightHeight = attrValue;
                                            else if( attrName == _T("VALNMR") )
                                                lightNominalRange = attrValue;
                                            else if( attrName == _T("OBJNAM") )
                                                lightName = attrValue;
                                        }
                                    }

                                    if( feature == _T("LIGHTS") ) {
                                        // +33B: deduplicate only genuinely identical
                                        // LIGHTS records. Sector/category/exhibition
                                        // differences must survive as separate lights.
                                        bool lightAlreadyAdded = false;

                                        for( size_t li = 0;
                                             li < candidate.lightCharacters.GetCount();
                                             ++li ) {

                                            if( candidate.lightColours[li] == lightColour &&
                                                candidate.lightCharacters[li] == lightCharacter &&
                                                candidate.lightGroups[li] == lightGroup &&
                                                candidate.lightPeriods[li] == lightPeriod &&
                                                candidate.lightSector1[li] == lightSector1 &&
                                                candidate.lightSector2[li] == lightSector2 &&
                                                candidate.lightCategories[li] == lightCategory &&
                                                candidate.lightExhibitions[li] == lightExhibition &&
                                                candidate.lightHeights[li] == lightHeight &&
                                                candidate.lightNominalRanges[li] == lightNominalRange &&
                                                candidate.lightNames[li] == lightName ) {

                                                lightAlreadyAdded = true;
                                                break;
                                            }
                                        }

                                        if( !lightAlreadyAdded ) {
                                            candidate.lightColours.Add(lightColour);
                                            candidate.lightCharacters.Add(lightCharacter);
                                            candidate.lightGroups.Add(lightGroup);
                                            candidate.lightPeriods.Add(lightPeriod);
                                            candidate.lightSector1.Add(lightSector1);
                                            candidate.lightSector2.Add(lightSector2);
                                            candidate.lightCategories.Add(lightCategory);
                                            candidate.lightExhibitions.Add(lightExhibition);
                                            candidate.lightHeights.Add(lightHeight);
                                            candidate.lightNominalRanges.Add(lightNominalRange);
                                            candidate.lightNames.Add(lightName);
                                        }
                                    }

                                }

                                std::map<wxString, GEMRouteHit>::iterator hitIt =
                                    routeHits.find(key);

                                if( hitIt == routeHits.end() ) {

                                    GEMRouteHit h;
                                    h.feature = feature;
                                    h.index = eo->Index;
                                    h.lat = 0.0;
                                    h.lon = 0.0;
                                    h.hasPosition = false;
                                    h.hits = 0;
                                    h.enriched = true;

                                    if( eo->npt == 1 ) {
                                        double olon, olat;

                                        fromSM_Plugin(
                                            (eo->x * eo->x_rate) +
                                                eo->x_origin,
                                            (eo->y * eo->y_rate) +
                                                eo->y_origin,
                                            m_ref_lat,
                                            m_ref_lon,
                                            &olat,
                                            &olon
                                        );

                                        if( olon > 180.0 )
                                            olon -= 360.0;

                                        h.lat = olat;
                                        h.lon = olon;
                                        h.hasPosition = true;
                                    }

                                    routeHits[key] = h;
                                }
                                else {
                                    hitIt->second.enriched = true;
                                }
                            }

                            if( !candidate.primaryFeature.IsEmpty() )
                                gemCandidates[candidateKey] = candidate;

                            delete exactObjects;
                        }
                    }

                    g_gemInternalScan = false;

                    wxString routeJson;

                    routeJson << _T("{\n");
                    routeJson <<
                        _T("  \"gem_format\": \"route-query-test-v2\",\n");

                    routeJson << wxString::Format(
                        _T(
                            "  \"route\": {"
                            "\"start\": {\"latitude\": %.8f, \"longitude\": %.8f}, "
                            "\"end\": {\"latitude\": %.8f, \"longitude\": %.8f}, "
                            "\"length_metres\": %.1f},\n"
                        ),
                        routeLat[0], routeLon[0],
                        routeLat[routePointCount - 1],
                        routeLon[routePointCount - 1],
                        routeLength
                    );

                    routeJson << wxString::Format(
                        _T(
                            "  \"sampling\": {"
                            "\"waypoint_count\": %d, "
                            "\"leg_count\": %d, "
                            "\"along_track_spacing_metres\": 100, "
                            "\"cross_track_offsets_metres\": [-50, 0, 50], "
                            "\"sample_count\": %lu, "
                            "\"enrichment_queries\": %lu},\n"
                        ),
                        routePointCount,
                        routePointCount - 1,
                        routeSamples,
                        enrichmentQueries
                    );

                    routeJson << _T("  \"objects\": [\n");

                    bool firstRouteHit = true;

                    for(
                        std::map<wxString, GEMRouteHit>::const_iterator it =
                            routeHits.begin();
                        it != routeHits.end();
                        ++it
                    ) {
                        const GEMRouteHit &h = it->second;

                        if( !firstRouteHit )
                            routeJson << _T(",\n");

                        routeJson <<
                            _T("    {\"feature\": \"") <<
                            GEMJsonEscape(h.feature) <<
                            _T("\", \"index\": ") <<
                            wxString::Format(
                                _T("%d"),
                                h.index
                            );

                        if( h.hasPosition ) {
                            routeJson << wxString::Format(
                                _T(
                                    ", \"latitude\": %.8f, "
                                    "\"longitude\": %.8f"
                                ),
                                h.lat,
                                h.lon
                            );
                        }

                        routeJson << wxString::Format(
                            _T(
                                ", \"corridor_hits\": %lu, "
                                "\"exact_position_enrichment\": %s}"
                            ),
                            h.hits,
                            h.enriched ? _T("true") : _T("false")
                        );

                        firstRouteHit = false;
                    }

                    routeJson << _T("\n  ],\n");

                    routeJson << wxString::Format(
                        _T("  \"object_count\": %lu\n"),
                        (unsigned long)routeHits.size()
                    );

                    routeJson << _T("}\n");

                    wxString routeOutputPath =
                        gemDir +
                        wxFILE_SEP_PATH +
                        _T("gem-route-test.json");

                    wxFFile routeOutput;

                    if( routeOutput.Open(
                            routeOutputPath,
                            _T("wb")
                        )
                    ) {
                        bool ok =
                            routeOutput.Write(
                                routeJson,
                                wxConvUTF8
                            );

                        routeOutput.Close();

                        wxLogMessage(
                            ok
                                ? _T(
                                    "GEMROUTE +19 WRITE OK "
                                    "objects=%lu samples=%lu enrich=%lu path=%s"
                                )
                                : _T(
                                    "GEMROUTE +19 WRITE FAILED "
                                    "objects=%lu samples=%lu enrich=%lu path=%s"
                                ),
                            (unsigned long)routeHits.size(),
                            routeSamples,
                            enrichmentQueries,
                            routeOutputPath.c_str()
                        );
                    }

                    // +13 presentation normalization.
                    // Preserve raw decoded S-57 strings and derive clean text/code
                    // separately.  Values without a trailing "(number)" remain text-only.
                    struct GEMNormValue {
                        wxString raw;
                        wxString text;
                        wxString code;
                    };

                    // Local lambda-style helper is avoided for compatibility with
                    // the older Windows build toolchain used by this plugin.
                    #define GEM_NORMALIZE_VALUE(INPUT, OUT)                           \
                        OUT.raw = INPUT;                                               \
                        OUT.text = INPUT;                                              \
                        OUT.code = _T("");                                             \
                        {                                                              \
                            int gemClose = OUT.text.Find(')', true);                   \
                            int gemOpen = OUT.text.Find('(', true);                    \
                            if( gemOpen != wxNOT_FOUND &&                              \
                                gemClose == (int)OUT.text.Length() - 1 &&              \
                                gemOpen < gemClose ) {                                 \
                                wxString gemMaybeCode =                                \
                                    OUT.text.Mid(gemOpen + 1, gemClose - gemOpen - 1); \
                                long gemCodeNumber = 0;                                \
                                if( gemMaybeCode.ToLong(&gemCodeNumber) ) {            \
                                    OUT.code = gemMaybeCode;                           \
                                    OUT.text = OUT.text.Left(gemOpen);                 \
                                    OUT.text.Trim(true).Trim(false);                   \
                                }                                                      \
                            }                                                          \
                        }

                    // +18 viewport/chart-state diagnostic.
                    // Acquisition logic is deliberately unchanged from +17.
                    wxString vpJson;
                    vpJson << _T("{\n");
                    vpJson << _T("  \"gem_format\": \"viewport-diagnostic-v1\",\n");
                    vpJson << _T("  \"scanner_version\": \"GEM +18\",\n");
                    vpJson << wxString::Format(
                        _T("  \"centre\": {\"latitude\": %.8f, \"longitude\": %.8f},\n"),
                        g_gemQueryVP.clat, g_gemQueryVP.clon);
                    vpJson << wxString::Format(
                        _T("  \"bounds\": {\"lat_min\": %.8f, \"lat_max\": %.8f, "
                           "\"lon_min\": %.8f, \"lon_max\": %.8f},\n"),
                        g_gemQueryVP.lat_min, g_gemQueryVP.lat_max,
                        g_gemQueryVP.lon_min, g_gemQueryVP.lon_max);
                    vpJson << wxString::Format(
                        _T("  \"pixel_size\": {\"width\": %d, \"height\": %d},\n"),
                        g_gemQueryVP.pix_width, g_gemQueryVP.pix_height);
                    vpJson << wxString::Format(
                        _T("  \"view_scale_ppm\": %.12g,\n"),
                        g_gemQueryVP.view_scale_ppm);
                    vpJson << wxString::Format(
                        _T("  \"chart_scale\": %.12g,\n"),
                        g_gemQueryVP.chart_scale);
                    vpJson << wxString::Format(
                        _T("  \"rotation_radians\": %.12g,\n"),
                        g_gemQueryVP.rotation);
                    vpJson << wxString::Format(
                        _T("  \"skew_radians\": %.12g,\n"),
                        g_gemQueryVP.skew);

                    // +19: identify the eSENCChart instance which is actually
                    // servicing this Object Query.  GetChartExtent() and
                    // GetNativeScale() are public eSENCChart accessors in the
                    // pinned source.  m_FullPath is the inherited ChartBase
                    // path already used by eSENCChart.cpp itself.
                    ExtentPI gemChartExtent;
                    bool gemHaveChartExtent = GetChartExtent(&gemChartExtent);
                    vpJson << _T("  \"active_chart\": {\n");
                    vpJson << wxString::Format(
                        _T("    \"path\": \"%s\",\n"),
                        GEMJsonEscape(m_FullPath).c_str());
                    vpJson << wxString::Format(
                        _T("    \"native_scale\": %d,\n"),
                        GetNativeScale());
                    vpJson << wxString::Format(
                        _T("    \"coverage_entries\": %d,\n"),
                        GetCOVREntries());
                    vpJson << wxString::Format(
                        _T("    \"no_coverage_entries\": %d,\n"),
                        GetNoCOVREntries());
                    if( gemHaveChartExtent ) {
                        vpJson << wxString::Format(
                            _T("    \"extent\": {\"south\": %.8f, \"north\": %.8f, "
                               "\"west\": %.8f, \"east\": %.8f}\n"),
                            gemChartExtent.SLAT, gemChartExtent.NLAT,
                            gemChartExtent.WLON, gemChartExtent.ELON);
                    } else {
                        vpJson << _T("    \"extent\": null\n");
                    }
                    vpJson << _T("  },\n");

                    vpJson << wxString::Format(
                        _T("  \"route\": {\"length_metres\": %.1f, "
                           "\"waypoint_count\": %d, \"sample_count\": %lu},\n"),
                        routeLength, routePointCount, routeSamples);
                    vpJson << _T("  \"note\": \"Cached viewport from the normal Object Query which seeded the route scan\"\n");
                    vpJson << _T("}\n");

                    wxString vpPath =
                        gemDir + wxFILE_SEP_PATH + _T("gem-viewport-diagnostic.json");
                    wxFFile vpFile;
                    if( vpFile.Open(vpPath, _T("wb")) ) {
                        bool vpOK = vpFile.Write(vpJson, wxConvUTF8);
                        vpFile.Close();
                        wxLogMessage(
                            vpOK
                                ? _T("GEMVIEW +19 WRITE OK path=%s")
                                : _T("GEMVIEW +19 WRITE FAILED path=%s"),
                            vpPath.c_str());
                    }

                    // +17/+18 route-return diagnostic. The existing route and
                    // candidate outputs remain unchanged.
                    wxString diagJson;
                    diagJson << _T("{\n");
                    diagJson << _T("  \"gem_format\": \"route-diagnostic-v1\",\n");
                    diagJson << wxString::Format(
                        _T("  \"route_length_metres\": %.1f,\n"), routeLength);
                    diagJson << wxString::Format(
                        _T("  \"waypoint_count\": %d,\n"), routePointCount);
                    diagJson << _T("  \"bands\": [\n");
                    for( int di = 0; di < 5; ++di ) {
                        if( di ) diagJson << _T(",\n");
                        diagJson << wxString::Format(
                            _T("    {\"band\": %d, \"queries\": %lu, \"returned_objects\": %lu}"),
                            di + 1, gemDiagQueries[di], gemDiagObjects[di]);
                    }
                    diagJson << _T("\n  ]\n}\n");

                    wxString diagPath =
                        gemDir + wxFILE_SEP_PATH + _T("gem-route-diagnostic.json");
                    wxFFile diagFile;
                    if( diagFile.Open(diagPath, _T("wb")) ) {
                        bool diagOK = diagFile.Write(diagJson, wxConvUTF8);
                        diagFile.Close();
                        wxLogMessage(
                            diagOK
                                ? _T("GEMDIAG +19 WRITE OK path=%s")
                                : _T("GEMDIAG +19 WRITE FAILED path=%s"),
                            diagPath.c_str());
                    }

                    wxString candidatesJson;
                    candidatesJson << _T("{\n");
                    candidatesJson << _T("  \"gem_format\": \"route-navigation-candidates-v2\",\n");
                    candidatesJson << _T("  \"candidates\": [\n");

                    bool firstCandidate = true;

                    for(
                        std::map<wxString, GEMCandidate>::const_iterator cit =
                            gemCandidates.begin();
                        cit != gemCandidates.end();
                        ++cit
                    ) {
                        const GEMCandidate &c = cit->second;

                        if( !firstCandidate )
                            candidatesJson << _T(",\n");

                        candidatesJson << _T("    {\n");
                        candidatesJson << _T("      \"name\": \"")
                                       << GEMJsonEscape(c.name)
                                       << _T("\",\n");
                        candidatesJson << _T("      \"primary_feature\": \"")
                                       << GEMJsonEscape(c.primaryFeature)
                                       << _T("\",\n");
                        candidatesJson << wxString::Format(
                            _T("      \"primary_index\": %d,\n"),
                            c.primaryIndex
                        );
                        candidatesJson << wxString::Format(
                            _T("      \"position\": {\"latitude\": %.8f, \"longitude\": %.8f},\n"),
                            c.lat, c.lon
                        );
                        GEMNormValue normShape;
                        GEMNormValue normCategory;
                        GEMNormValue normColour;
                        GEM_NORMALIZE_VALUE(c.shape, normShape);
                        GEM_NORMALIZE_VALUE(c.category, normCategory);
                        GEM_NORMALIZE_VALUE(c.colour, normColour);

                        candidatesJson << _T("      \"shape\": {\"raw\": \"")
                                       << GEMJsonEscape(normShape.raw)
                                       << _T("\", \"text\": \"")
                                       << GEMJsonEscape(normShape.text)
                                       << _T("\", \"code\": \"")
                                       << GEMJsonEscape(normShape.code)
                                       << _T("\"},\n");
                        candidatesJson << _T("      \"category\": {\"raw\": \"")
                                       << GEMJsonEscape(normCategory.raw)
                                       << _T("\", \"text\": \"")
                                       << GEMJsonEscape(normCategory.text)
                                       << _T("\", \"code\": \"")
                                       << GEMJsonEscape(normCategory.code)
                                       << _T("\"},\n");
                        candidatesJson << _T("      \"colour\": {\"raw\": \"")
                                       << GEMJsonEscape(normColour.raw)
                                       << _T("\", \"text\": \"")
                                       << GEMJsonEscape(normColour.text)
                                       << _T("\", \"code\": \"")
                                       << GEMJsonEscape(normColour.code)
                                       << _T("\"},\n");
                        candidatesJson << _T("      \"information\": \"")
                                       << GEMJsonEscape(c.information)
                                       << _T("\",\n");
                        candidatesJson << _T("      \"source\": {\"SORDAT\": \"")
                                       << GEMJsonEscape(c.sourceDate)
                                       << _T("\", \"SORIND\": \"")
                                       << GEMJsonEscape(c.sourceIndication)
                                       << _T("\"},\n");              
                        candidatesJson << _T("      \"chart_sources\": [");

                        wxString gemProvenanceKey = wxString::Format(
                            _T("%.7f:%.7f"),
                            c.lat,
                            c.lon);

                        std::map<wxString, wxArrayString>::const_iterator
                            gemSourceIt =
                                gemCandidateChartSources.find(gemProvenanceKey);

                        if(gemSourceIt != gemCandidateChartSources.end()) {
                            const wxArrayString &gemSources =
                                gemSourceIt->second;

                            for(size_t gemSI = 0;
                                gemSI < gemSources.GetCount();
                                ++gemSI) {

                                if(gemSI)
                                    candidatesJson << _T(", ");

                                wxString gemSource = gemSources[gemSI];
                                wxString gemChartName =
                                    gemSource.BeforeLast('|');
                                wxString gemScaleText =
                                    gemSource.AfterLast('|');

                                long gemNativeScale = 0;
                                gemScaleText.ToLong(&gemNativeScale);

                                candidatesJson
                                    << _T("{\"chart\": \"")
                                    << GEMJsonEscape(gemChartName)
                                    << _T("\", \"native_scale\": ")
                                    << wxString::Format(
                                           _T("%ld"),
                                           gemNativeScale)
                                    << _T("}");
                            }
                        }

                        candidatesJson << _T("],\n");

                        wxString displayLine = normCategory.text;
                        if( !normColour.text.IsEmpty() ) {
                            if( !displayLine.IsEmpty() ) displayLine << _T(" - ");
                            displayLine << normColour.text;
                        }
                        if( !normShape.text.IsEmpty() ) {
                            if( !displayLine.IsEmpty() ) displayLine << _T(" ");
                            displayLine << normShape.text;
                        }

                        candidatesJson << _T("      \"display\": {\"name\": \"")
                                       << GEMJsonEscape(c.name)
                                       << _T("\", \"description\": \"")
                                       << GEMJsonEscape(displayLine)
                                       << _T("\"},\n");

                        candidatesJson << _T("      \"components\": [");
                        for( size_t ci = 0;
                             ci < c.componentFeatures.GetCount();
                             ++ci ) {
                            if( ci ) candidatesJson << _T(", ");
                            candidatesJson << _T("{\"feature\": \"")
                                           << GEMJsonEscape(c.componentFeatures[ci])
                                           << _T("\", \"index\": ")
                                           << wxString::Format(
                                               _T("%d"),
                                               c.componentIndexes[ci]
                                           )
                                           << _T("}");
                        }
                        candidatesJson << _T("],\n");

                        candidatesJson << _T("      \"lights\": [");

                        for( size_t li = 0;
                             li < c.lightCharacters.GetCount();
                             ++li ) {

                            if( li )
                                candidatesJson << _T(", ");

                            GEMNormValue lightColour;
                            GEMNormValue lightCharacter;
                            GEMNormValue lightCategory;
                            GEMNormValue lightExhibition;

                            GEM_NORMALIZE_VALUE(
                                c.lightColours[li],
                                lightColour
                            );

                            GEM_NORMALIZE_VALUE(
                                c.lightCharacters[li],
                                lightCharacter
                            );

                            GEM_NORMALIZE_VALUE(
                                c.lightCategories[li],
                                lightCategory
                            );

                            GEM_NORMALIZE_VALUE(
                                c.lightExhibitions[li],
                                lightExhibition
                            );

                            candidatesJson
                                << _T("{\"name\": \"")
                                << GEMJsonEscape(c.lightNames[li])

                                << _T("\", \"colour\": {\"raw\": \"")
                                << GEMJsonEscape(lightColour.raw)
                                << _T("\", \"text\": \"")
                                << GEMJsonEscape(lightColour.text)
                                << _T("\", \"code\": \"")
                                << GEMJsonEscape(lightColour.code)

                                << _T("\"}, \"character\": {\"raw\": \"")
                                << GEMJsonEscape(lightCharacter.raw)
                                << _T("\", \"text\": \"")
                                << GEMJsonEscape(lightCharacter.text)
                                << _T("\", \"code\": \"")
                                << GEMJsonEscape(lightCharacter.code)

                                << _T("\"}, \"group\": \"")
                                << GEMJsonEscape(c.lightGroups[li])

                                << _T("\", \"period\": \"")
                                << GEMJsonEscape(c.lightPeriods[li])

                                << _T("\", \"sector\": {\"start\": \"")
                                << GEMJsonEscape(c.lightSector1[li])
                                << _T("\", \"end\": \"")
                                << GEMJsonEscape(c.lightSector2[li])

                                << _T("\"}, \"category\": {\"raw\": \"")
                                << GEMJsonEscape(lightCategory.raw)
                                << _T("\", \"text\": \"")
                                << GEMJsonEscape(lightCategory.text)
                                << _T("\", \"code\": \"")
                                << GEMJsonEscape(lightCategory.code)

                                << _T("\"}, \"exhibition\": {\"raw\": \"")
                                << GEMJsonEscape(lightExhibition.raw)
                                << _T("\", \"text\": \"")
                                << GEMJsonEscape(lightExhibition.text)
                                << _T("\", \"code\": \"")
                                << GEMJsonEscape(lightExhibition.code)

                                << _T("\"}, \"height\": \"")
                                << GEMJsonEscape(c.lightHeights[li])

                                << _T("\", \"nominal_range\": \"")
                                << GEMJsonEscape(c.lightNominalRanges[li])

                                << _T("\"}");
                        }

                        candidatesJson << _T("]\n");
                        candidatesJson << _T("    }");

                        firstCandidate = false;
                    }

                    candidatesJson << _T("\n  ],\n");
                    candidatesJson << wxString::Format(
                        _T("  \"candidate_count\": %lu\n"),
                        (unsigned long)gemCandidates.size()
                    );
                    candidatesJson << _T("}\n");

                    wxString candidatesPath =
                        gemDir +
                        wxFILE_SEP_PATH +
                        _T("gem-route-candidates-v2.json");

                    wxFFile candidatesFile;

                    if( candidatesFile.Open(candidatesPath, _T("wb")) ) {
                        bool candidatesOK =
                            candidatesFile.Write(
                                candidatesJson,
                                wxConvUTF8
                            );

                        candidatesFile.Close();

                        wxLogMessage(
                            candidatesOK
                                ? _T(
                                    "GEMCANDIDATES +19 WRITE OK "
                                    "candidates=%lu path=%s"
                                )
                                : _T(
                                    "GEMCANDIDATES +19 WRITE FAILED "
                                    "candidates=%lu path=%s"
                                ),
                            (unsigned long)gemCandidates.size(),
                            candidatesPath.c_str()
                        );
                    }

                    #undef GEM_NORMALIZE_VALUE
                }
                else {
                    wxLogMessage(
                        _T(
                            "GEMROUTE +19 SKIPPED: "
                            "route length %.1f m outside diagnostic limit"
                        ),
                        routeLength
                    );
                }
            }
            else {
                wxLogMessage(
                    _T(
                        "GEMROUTE +19 SKIPPED: "
                        "gem-route-query.json must contain 2 to 32 "
                        "lat/lon route points"
                    )
                );
            }
        }
    }

    // Add the additional info files
""",
    "selected export and +10 diagnostic"
)


# +20 diagnostic only: register chart objects which OpenCPN itself creates.
a = "eSENCChart::eSENCChart()\n{"
b = '''static std::vector<eSENCChart *> g_gemLiveCharts;

eSENCChart::eSENCChart()
{
    g_gemLiveCharts.push_back(this);'''
if a not in chart:
    raise RuntimeError("+20 constructor anchor not found")
chart = chart.replace(a, b, 1)

a = "eSENCChart::~eSENCChart()\n{\n"
b = '''eSENCChart::~eSENCChart()
{
    for(std::vector<eSENCChart *>::iterator it = g_gemLiveCharts.begin();
        it != g_gemLiveCharts.end(); ++it) {
        if(*it == this) {
            g_gemLiveCharts.erase(it);
            break;
        }
    }

'''
if a not in chart:
    raise RuntimeError("+20 destructor anchor not found")
chart = chart.replace(a, b, 1)

a = '''                    vpJson << wxString::Format(
                        _T("  \\"route\\": {\\"length_metres\\": %.1f, "
                           "\\"waypoint_count\\": %d, \\"sample_count\\": %lu},\\n"),
                        routeLength, routePointCount, routeSamples);'''
b = '''                    vpJson << _T("  \\"live_charts\\": [\\n");
                    for(size_t gemChartIndex = 0; gemChartIndex < g_gemLiveCharts.size(); ++gemChartIndex) {
                        eSENCChart *gemChart = g_gemLiveCharts[gemChartIndex];
                        if(!gemChart) continue;
                        ExtentPI gemExtent;
                        bool gemExtentOK = gemChart->GetChartExtent(&gemExtent);
                        vpJson << _T("    {");
                        vpJson << wxString::Format(
                            _T("\\"instance\\": \\"%p\\", \\"is_active\\": %s, "),
                            (void *)gemChart, gemChart == this ? _T("true") : _T("false"));
                        vpJson << wxString::Format(
                            _T("\\"path\\": \\"%s\\", \\"native_scale\\": %d, "),
                            GEMJsonEscape(gemChart->m_FullPath).c_str(), gemChart->GetNativeScale());
                        vpJson << wxString::Format(
                            _T("\\"coverage_entries\\": %d, \\"no_coverage_entries\\": %d, "),
                            gemChart->GetCOVREntries(), gemChart->GetNoCOVREntries());
                        if(gemExtentOK)
                            vpJson << wxString::Format(
                                _T("\\"extent\\": {\\"south\\": %.8f, \\"north\\": %.8f, \\"west\\": %.8f, \\"east\\": %.8f}"),
                                gemExtent.SLAT, gemExtent.NLAT, gemExtent.WLON, gemExtent.ELON);
                        else
                            vpJson << _T("\\"extent\\": null");
                        vpJson << _T("}");
                        if(gemChartIndex + 1 < g_gemLiveCharts.size()) vpJson << _T(",");
                        vpJson << _T("\\n");
                    }
                    vpJson << _T("  ],\\n");

                    vpJson << wxString::Format(
                        _T("  \\"route\\": {\\"length_metres\\": %.1f, "
                           "\\"waypoint_count\\": %d, \\"sample_count\\": %lu},\\n"),
                        routeLength, routePointCount, routeSamples);'''
if a not in chart:
    raise RuntimeError("+20 viewport route anchor not found")
chart = chart.replace(a, b, 1)

chart = chart.replace('\\"scanner_version\\": \\"GEM +18\\"', '\\"scanner_version\\": \\"GEM +20\\"')
chart = chart.replace('\\"scanner_version\\": \\"GEM +19\\"', '\\"scanner_version\\": \\"GEM +20\\"')
chart = chart.replace("GEMVIEW +19", "GEMVIEW +20")


# +21: dispatch to all already-live chart instances containing each coordinate.
old = '                                ListOfPI_S57Obj *routeObjects =\n                                    GetObjRuleListAtLatLon(\n                                        sampleLat, sampleLon,\n                                        g_gemQueryRadius, &routeVP);\n\n                                routeSamples++;'
new = '                                ListOfPI_S57Obj *routeObjects =\n                                    new ListOfPI_S57Obj;\n                                routeObjects->DeleteContents(true);\n\n                                for(size_t gemCI = 0; gemCI < g_gemLiveCharts.size(); ++gemCI) {\n                                    eSENCChart *gemChart = g_gemLiveCharts[gemCI];\n                                    if(!gemChart) continue;\n                                    ExtentPI gemExtent;\n                                    if(!gemChart->GetChartExtent(&gemExtent)) continue;\n                                    if(sampleLat < gemExtent.SLAT || sampleLat > gemExtent.NLAT ||\n                                       sampleLon < gemExtent.WLON || sampleLon > gemExtent.ELON) continue;\n\n                                    ListOfPI_S57Obj *gemObjects =\n                                        gemChart->GetObjRuleListAtLatLon(\n                                            sampleLat, sampleLon, g_gemQueryRadius, &routeVP);\n                                    if(gemObjects) {\n                                        for(ListOfPI_S57Obj::Node *gn = gemObjects->GetFirst();\n                                            gn; gn = gn->GetNext()) {\n                                            PI_S57Obj *go = gn->GetData();\n                                            PI_S57Obj *copy = new PI_S57Obj;\n                                            *copy = *go;\n                                            routeObjects->Append(copy);\n                                        }\n                                        gemObjects->DeleteContents(false);\n                                        delete gemObjects;\n                                    }\n                                }\n\n                                routeSamples++;'
if old not in chart:
    raise RuntimeError("+21 corridor anchor not found")
chart = chart.replace(old, new, 1)

old = '''                        ListOfPI_S57Obj *exactObjects =
                            GetObjRuleListAtLatLon(
                                (float)enrichPoints[ei].lat,
                                (float)enrichPoints[ei].lon,
                                g_gemQueryRadius,
                                &enrichVP
                            );

                        enrichmentQueries++;'''

new = '''                        ListOfPI_S57Obj *exactObjects =
                            new ListOfPI_S57Obj;
                        exactObjects->DeleteContents(true);

                        for(size_t gemCI = 0; gemCI < g_gemLiveCharts.size(); ++gemCI) {
                            eSENCChart *gemChart = g_gemLiveCharts[gemCI];
                            if(!gemChart) continue;

                            ExtentPI gemExtent;
                            if(!gemChart->GetChartExtent(&gemExtent)) continue;

                            if(enrichPoints[ei].lat < gemExtent.SLAT ||
                               enrichPoints[ei].lat > gemExtent.NLAT ||
                               enrichPoints[ei].lon < gemExtent.WLON ||
                               enrichPoints[ei].lon > gemExtent.ELON) continue;

                            ListOfPI_S57Obj *gemObjects =
                                gemChart->GetObjRuleListAtLatLon(
                                    (float)enrichPoints[ei].lat,
                                    (float)enrichPoints[ei].lon,
                                    g_gemQueryRadius,
                                    &enrichVP);

                            if(gemObjects) {
                                bool gemChartSuppliedCandidate = false;

                                for(ListOfPI_S57Obj::Node *gn = gemObjects->GetFirst();
                                    gn; gn = gn->GetNext()) {

                                    PI_S57Obj *go = gn->GetData();

                                    if(go && go->npt == 1) {
                                        double gemObjLat = go->m_lat;
                                        double gemObjLon = go->m_lon;

                                        if(gemObjLon > 180.0)
                                            gemObjLon -= 360.0;

                                        if(fabs(gemObjLat - enrichPoints[ei].lat) < 0.000002 &&
                                           fabs(gemObjLon - enrichPoints[ei].lon) < 0.000002) {
                                            gemChartSuppliedCandidate = true;
                                        }
                                    }

                                    PI_S57Obj *copy = new PI_S57Obj;
                                    *copy = *go;
                                    exactObjects->Append(copy);
                                }

                                if(gemChartSuppliedCandidate) {
                                    wxString gemProvenanceKey =
                                        wxString::Format(
                                            _T("%.7f:%.7f"),
                                            enrichPoints[ei].lat,
                                            enrichPoints[ei].lon);

                                    wxString gemChartSource =
                                        wxFileName(gemChart->m_FullPath).GetFullName() +
                                        wxString::Format(
                                            _T("|%d"),
                                            gemChart->GetNativeScale());

                                    wxArrayString &gemSources =
                                        gemCandidateChartSources[gemProvenanceKey];

                                    bool gemSourceAlreadyPresent = false;

                                    for(size_t gemSI = 0;
                                        gemSI < gemSources.GetCount();
                                        ++gemSI) {

                                        if(gemSources[gemSI] == gemChartSource) {
                                            gemSourceAlreadyPresent = true;
                                            break;
                                        }
                                    }

                                    if(!gemSourceAlreadyPresent)
                                        gemSources.Add(gemChartSource);
                                }

                                gemObjects->DeleteContents(false);
                                delete gemObjects;
                            }
                        }

                        enrichmentQueries++;'''

if old not in chart:
    raise RuntimeError("+21 enrichment anchor not found")
chart = chart.replace(old, new, 1)

chart = chart.replace('\"scanner_version\": \"GEM +20\"',
                      '\"scanner_version\": \"GEM +21\"')
chart = chart.replace("GEMVIEW +20", "GEMVIEW +21")


# +22 diagnostic: log implausibly distant point returns per chart before changing viewport mechanics.
old22 = """                                    if(gemObjects) {
                                        for(ListOfPI_S57Obj::Node *gn = gemObjects->GetFirst();
                                            gn; gn = gn->GetNext()) {
                                            PI_S57Obj *go = gn->GetData();
                                            PI_S57Obj *copy = new PI_S57Obj;
                                            *copy = *go;
                                            routeObjects->Append(copy);
                                        }
                                        gemObjects->DeleteContents(false);
                                        delete gemObjects;
                                    }"""
new22 = """                                    if(gemObjects) {
                                        for(ListOfPI_S57Obj::Node *gn = gemObjects->GetFirst();
                                            gn; gn = gn->GetNext()) {
                                            PI_S57Obj *go = gn->GetData();
                                            if(go && go->Primitive_type == GEO_POINT) {
                                                const double gemLatScale = 111320.0;
                                                const double gemLonScale = 111320.0 * cos(sampleLat * M_PI / 180.0);
                                                const double gemDN = (go->m_lat - sampleLat) * gemLatScale;
                                                const double gemDE = (go->m_lon - sampleLon) * gemLonScale;
                                                const double gemDist = sqrt(gemDN * gemDN + gemDE * gemDE);
                                                if(gemDist > 500.0) {
                                                    wxLogMessage(_T("GEMPOINT +22 FAR chart=%s feature=%s index=%d sample=%.7f,%.7f object=%.7f,%.7f distance=%.1fm"),
                                                        gemChart->m_FullPath.c_str(),
                                                        wxString(go->FeatureName, wxConvUTF8).c_str(), go->Index,
                                                        sampleLat, sampleLon, go->m_lat, go->m_lon, gemDist);
                                                }
                                            }
                                            PI_S57Obj *copy = new PI_S57Obj;
                                            *copy = *go;
                                            routeObjects->Append(copy);
                                        }
                                        gemObjects->DeleteContents(false);
                                        delete gemObjects;
                                    }"""
if old22 not in chart:
    raise RuntimeError("+22 corridor object-loop anchor not found")
chart = chart.replace(old22, new22, 1)
for oldver in ("GEM +18", "GEM +19", "GEM +20", "GEM +21"):
    chart = chart.replace(oldver, "GEM +22")
for oldver in ("GEMVIEW +18", "GEMVIEW +19", "GEMVIEW +20", "GEMVIEW +21"):
    chart = chart.replace(oldver, "GEMVIEW +22")

# +23 candidate-only proximity sweep: preserve the +/-50m context scan, but
# discover physical buoy/beacon primaries to 1000m and feed them into the
# existing exact-position enrichment/candidate assembler.
marker = """                    // Second pass: exact-position enrichment for point
                    // navigation marks discovered by the corridor."""
insert = r"""                    // +28 CANDIDATE PROXIMITY SWEEP
                    const double gemCandidateLimitMetres = 1000.0;
                    const double gemCandidateGridMetres = 100.0;
                    unsigned long gemCandidateQueries = 0;
                    unsigned long gemCandidatePrimaryHits = 0;

                    for( int leg = 0; leg < routePointCount - 1; ++leg ) {
                        const double meanLatRad = ((routeLat[leg] + routeLat[leg + 1]) * 0.5) * pi11 / 180.0;
                        const double metresPerDegLon23 = metresPerDegLat11 * cos(meanLatRad);
                        const double dNorth = (routeLat[leg + 1] - routeLat[leg]) * metresPerDegLat11;
                        const double dEast = (routeLon[leg + 1] - routeLon[leg]) * metresPerDegLon23;
                        const double legLength = sqrt((dNorth*dNorth) + (dEast*dEast));
                        if( legLength <= 0.1 ) continue;
                        const double uNorth = dNorth / legLength, uEast = dEast / legLength;
                        const double pNorth = -uEast, pEast = uNorth;
                        int alongSteps = (int)ceil(legLength / gemCandidateGridMetres);
                        if( alongSteps < 1 ) alongSteps = 1;

                        for( int step = 0; step <= alongSteps; ++step ) {
                            double along = (step == alongSteps) ? legLength : step * gemCandidateGridMetres;
                            if( along > legLength ) along = legLength;
                            for( int oi = -10; oi <= 10; ++oi ) {
                                const double offset = oi * gemCandidateGridMetres;
                                const double sampleEast = (uEast*along) + (pEast*offset);
                                const double sampleNorth = (uNorth*along) + (pNorth*offset);
                                const float sampleLat = (float)(routeLat[leg] + sampleNorth/metresPerDegLat11);
                                const float sampleLon = (float)(routeLon[leg] + sampleEast/metresPerDegLon23);

                                PlugIn_ViewPort candidateVP = g_gemQueryVP;
                                const double vpDLat = sampleLat - candidateVP.clat;
                                const double vpDLon = sampleLon - candidateVP.clon;
                                candidateVP.clat = sampleLat; candidateVP.clon = sampleLon;
                                candidateVP.lat_min += vpDLat; candidateVP.lat_max += vpDLat;
                                candidateVP.lon_min += vpDLon; candidateVP.lon_max += vpDLon;

                                for(size_t gemCI=0; gemCI<g_gemLiveCharts.size(); ++gemCI) {
                                    eSENCChart *gemChart=g_gemLiveCharts[gemCI]; if(!gemChart) continue;
                                    ExtentPI gemExtent; if(!gemChart->GetChartExtent(&gemExtent)) continue;
                                    if(sampleLat<gemExtent.SLAT || sampleLat>gemExtent.NLAT || sampleLon<gemExtent.WLON || sampleLon>gemExtent.ELON) continue;
                                    ListOfPI_S57Obj *candidateObjects = gemChart->GetObjRuleListAtLatLon(sampleLat,sampleLon,g_gemQueryRadius,&candidateVP);
                                    gemCandidateQueries++;
                                    if(!candidateObjects) continue;
                                    for(ListOfPI_S57Obj::Node *cn=candidateObjects->GetFirst(); cn; cn=cn->GetNext()) {
                                        PI_S57Obj *co=cn->GetData(); if(!co || co->npt!=1) continue;
                                        wxString feature(co->FeatureName,wxConvUTF8);
                                        bool primary = feature==_T("BOYLAT") || feature==_T("BOYCAR") || feature==_T("BOYSAW") || feature==_T("BOYISD") || feature==_T("BOYSPP") || feature==_T("BCNLAT") || feature==_T("BCNCAR") || feature==_T("BCNSAW") || feature==_T("BCNSPP");
                                        if(!primary) continue;
                                        double objectLon,objectLat;
                                        fromSM_Plugin((co->x*co->x_rate)+co->x_origin,(co->y*co->y_rate)+co->y_origin,m_ref_lat,m_ref_lon,&objectLat,&objectLon);
                                        if(objectLon>180.0) objectLon-=360.0;

                                        double minDistance=1.0e30;
                                        for(int dl=0; dl<routePointCount-1; ++dl) {
                                            const double localMeanLat=((routeLat[dl]+routeLat[dl+1]+objectLat)/3.0)*pi11/180.0;
                                            const double mLon=metresPerDegLat11*cos(localMeanLat);
                                            const double ax=(routeLon[dl]-objectLon)*mLon, ay=(routeLat[dl]-objectLat)*metresPerDegLat11;
                                            const double bx=(routeLon[dl+1]-objectLon)*mLon, by=(routeLat[dl+1]-objectLat)*metresPerDegLat11;
                                            const double vx=bx-ax, vy=by-ay, vv=vx*vx+vy*vy;
                                            double q=0.0; if(vv>0.000001) q=-((ax*vx)+(ay*vy))/vv;
                                            if(q<0.0) q=0.0; if(q>1.0) q=1.0;
                                            const double px=ax+q*vx, py=ay+q*vy;
                                            const double d=sqrt(px*px+py*py); if(d<minDistance) minDistance=d;
                                        }
                                        if(minDistance<=gemCandidateLimitMetres) {
                                            wxString key=feature+wxString::Format(_T(":%d"),co->Index);
                                            std::map<wxString,GEMRouteHit>::iterator hitIt=routeHits.find(key);
                                            if(hitIt==routeHits.end()) {
                                                GEMRouteHit h; h.feature=feature; h.index=co->Index; h.lat=objectLat; h.lon=objectLon; h.hasPosition=true; h.hits=0; h.enriched=false; routeHits[key]=h;
                                            }
                                            gemCandidatePrimaryHits++;
                                        }
                                    }
                                    delete candidateObjects;
                                }
                            }
                        }
                    }
                    wxLogMessage(_T("GEMPROX +28 queries=%lu primary_hits=%lu limit=%.0fm"),gemCandidateQueries,gemCandidatePrimaryHits,gemCandidateLimitMetres);

"""
if marker not in chart: raise RuntimeError('+28 marker not found')
chart=chart.replace(marker,insert+marker,1)
for v in ('GEM +18','GEM +19','GEM +20','GEM +21','GEM +22'): chart=chart.replace(v,'GEM +28')
for v in ('GEMVIEW +18','GEMVIEW +19','GEMVIEW +20','GEMVIEW +21','GEMVIEW +22'): chart=chart.replace(v,'GEMVIEW +28')


# +28 identity cleanup: the cumulative source still contains historical
# +19/+22 labels.  Normalize the route-related labels so the runtime log
# proves exactly which experimental build is active.
for old, new in (
    ("GEMPOINT +22", "GEMPOINT +28"),
    ("GEMROUTE +19", "GEMROUTE +28"),
    ("GEMDIAG +19", "GEMDIAG +28"),
    ("GEMCANDIDATES +19", "GEMCANDIDATES +28"),
    ('"scanner_version": "GEM +22"', '"scanner_version": "GEM +28"'),
):
    chart = chart.replace(old, new)


# +29: peer-chart coordinate correctness and cross-chart identity.
# PI_S57Obj::m_lat/m_lon is already the chart object's geographic position.
# Do not reconstruct peer-chart positions with `this->m_ref_lat/m_ref_lon`,
# because `this` is the chart whose Object Query triggered the scan, not
# necessarily the peer chart which supplied the object.
chart = chart.replace(
'''                                        wxString key =
                                            feature + wxString::Format(
                                                _T(\":%d\"), ro->Index);''',
'''                                        wxString key =
                                            feature + wxString::Format(_T(\":%d\"), ro->Index);
                                        if( ro->npt == 1 )
                                            key += wxString::Format(_T(\":%.7f:%.7f\"),
                                                ro->m_lat, ro->m_lon);''', 1)

chart = chart.replace(
'''                                            if( ro->npt == 1 ) {
                                                double olon, olat;
                                                fromSM_Plugin(
                                                    (ro->x * ro->x_rate) +
                                                        ro->x_origin,
                                                    (ro->y * ro->y_rate) +
                                                        ro->y_origin,
                                                    m_ref_lat, m_ref_lon,
                                                    &olat, &olon);
                                                if( olon > 180.0 )
                                                    olon -= 360.0;
                                                h.lat = olat;
                                                h.lon = olon;
                                                h.hasPosition = true;
                                            }''',
'''                                            if( ro->npt == 1 ) {
                                                h.lat = ro->m_lat;
                                                h.lon = ro->m_lon;
                                                if( h.lon > 180.0 ) h.lon -= 360.0;
                                                h.hasPosition = true;
                                            }''', 1)

chart = chart.replace(
'''                                wxString key =
                                    feature +
                                    wxString::Format(
                                        _T(\":%d\"),
                                        eo->Index
                                    );''',
'''                                wxString key =
                                    feature + wxString::Format(_T(\":%d\"), eo->Index);
                                if( eo->npt == 1 )
                                    key += wxString::Format(_T(\":%.7f:%.7f\"),
                                        eo->m_lat, eo->m_lon);''', 1)

chart = chart.replace(
'''                                if( eo->npt == 1 ) {
                                    fromSM_Plugin(
                                        (eo->x * eo->x_rate) + eo->x_origin,
                                        (eo->y * eo->y_rate) + eo->y_origin,
                                        m_ref_lat,
                                        m_ref_lon,
                                        &componentLat,
                                        &componentLon
                                    );

                                    if( componentLon > 180.0 )
                                        componentLon -= 360.0;''',
'''                                if( eo->npt == 1 ) {
                                    componentLat = eo->m_lat;
                                    componentLon = eo->m_lon;
                                    if( componentLon > 180.0 ) componentLon -= 360.0;''', 1)

chart = chart.replace(
'''                                    if( eo->npt == 1 ) {
                                        double olon, olat;

                                        fromSM_Plugin(
                                            (eo->x * eo->x_rate) +
                                                eo->x_origin,
                                            (eo->y * eo->y_rate) +
                                                eo->y_origin,
                                            m_ref_lat,
                                            m_ref_lon,
                                            &olat,
                                            &olon
                                        );

                                        if( olon > 180.0 )
                                            olon -= 360.0;

                                        h.lat = olat;
                                        h.lon = olon;
                                        h.hasPosition = true;
                                    }''',
'''                                    if( eo->npt == 1 ) {
                                        h.lat = eo->m_lat;
                                        h.lon = eo->m_lon;
                                        if( h.lon > 180.0 ) h.lon -= 360.0;
                                        h.hasPosition = true;
                                    }''', 1)

chart = chart.replace(
'''                                        double objectLon,objectLat;
                                        fromSM_Plugin((co->x*co->x_rate)+co->x_origin,(co->y*co->y_rate)+co->y_origin,m_ref_lat,m_ref_lon,&objectLat,&objectLon);
                                        if(objectLon>180.0) objectLon-=360.0;''',
'''                                        double objectLat=co->m_lat, objectLon=co->m_lon;
                                        if(objectLon>180.0) objectLon-=360.0;''', 1)

chart = chart.replace(
'''                                            wxString key=feature+wxString::Format(_T(\":%d\"),co->Index);''',
'''                                            wxString key=feature+wxString::Format(_T(\":%d:%.7f:%.7f\"),co->Index,objectLat,objectLon);''', 1)

# Make the runtime identity unmistakable.
chart = chart.replace("GEMPROX +28", "GEMPROX +29")
chart = chart.replace("GEMPOINT +28", "GEMPOINT +29")
chart = chart.replace("GEMROUTE +28", "GEMROUTE +29")
chart = chart.replace("GEMVIEW +28", "GEMVIEW +29")
chart = chart.replace("GEMDIAG +28", "GEMDIAG +29")
chart = chart.replace("GEMCANDIDATES +28", "GEMCANDIDATES +29")
chart = chart.replace('"scanner_version": "GEM +28"', '"scanner_version": "GEM +29"')

wx29 = '''    wxLogMessage(_T("GEMBUILD +29 peer-chart geographic coordinates active"));
'''
anchor29 = '''    wxLogMessage(
        _T("GEMPROBE +10 ENTER objects=%lu"),'''
if anchor29 in chart:
    chart = chart.replace(anchor29, wx29 + anchor29, 1)
else:
    raise RuntimeError("+29 startup/query marker anchor not found")

# +30 production-shaped candidate output.
chart = chart.replace('route-navigation-candidates-v2', 'route-navigation-candidates-v3')
chart = chart.replace('gem-route-candidates-v2.json', 'gem-route-candidates-v3.json')

old = "                        const GEMCandidate &c = cit->second;\n\n                        if( !firstCandidate )"
new = r'''                        const GEMCandidate &c = cit->second;

                        double gemMinRouteDistance = 1.0e30;
                        for( int gemDL = 0; gemDL < routePointCount - 1; ++gemDL ) {
                            const double gemMeanLat = ((routeLat[gemDL] + routeLat[gemDL + 1] + c.lat) / 3.0) * pi11 / 180.0;
                            const double gemMLon = metresPerDegLat11 * cos(gemMeanLat);
                            const double gemAX = (routeLon[gemDL] - c.lon) * gemMLon;
                            const double gemAY = (routeLat[gemDL] - c.lat) * metresPerDegLat11;
                            const double gemBX = (routeLon[gemDL + 1] - c.lon) * gemMLon;
                            const double gemBY = (routeLat[gemDL + 1] - c.lat) * metresPerDegLat11;
                            const double gemVX = gemBX - gemAX, gemVY = gemBY - gemAY;
                            const double gemVV = gemVX * gemVX + gemVY * gemVY;
                            double gemQ = gemVV > 0.000001 ? -((gemAX * gemVX) + (gemAY * gemVY)) / gemVV : 0.0;
                            if( gemQ < 0.0 ) gemQ = 0.0;
                            if( gemQ > 1.0 ) gemQ = 1.0;
                            const double gemPX = gemAX + gemQ * gemVX, gemPY = gemAY + gemQ * gemVY;
                            const double gemD = sqrt(gemPX * gemPX + gemPY * gemPY);
                            if( gemD < gemMinRouteDistance ) gemMinRouteDistance = gemD;
                        }
                        wxString gemRelevance = gemMinRouteDistance <= 100.0 ? _T("on_route") : _T("nearby");

                        if( !firstCandidate )'''
if old not in chart: raise RuntimeError('+30 distance anchor not found')
chart = chart.replace(old, new, 1)

old = "                            c.lat, c.lon\n                        );\n                        GEMNormValue normShape;"
new = r'''                            c.lat, c.lon
                        );
                        candidatesJson << wxString::Format(
                            _T("      \"distance_to_route_metres\": %.1f,\n"), gemMinRouteDistance);
                        candidatesJson << _T("      \"relevance\": \"") << gemRelevance << _T("\",\n");
                        GEMNormValue normShape;'''
if old not in chart: raise RuntimeError('+30 JSON distance anchor not found')
chart = chart.replace(old, new, 1)

# Clean the malformed text/code split returned for multi-valued enumerations.
old = '''                        GEM_NORMALIZE_VALUE(c.colour, normColour);\n\n                        candidatesJson << _T(\"      \\\"shape\\\": {\\\"raw\\\": \\\"\")'''
new = r'''                        GEM_NORMALIZE_VALUE(c.colour, normColour);

                        // +30: oeSENC multi-value decoded enums can arrive as
                        // "black, yellow2,6". Split the trailing numeric CSV
                        // from presentation text while preserving raw unchanged.
                        if( normColour.code.IsEmpty() && !normColour.text.IsEmpty() ) {
                            int gemDigit = wxNOT_FOUND;
                            for( size_t gemI = 0; gemI < normColour.text.Length(); ++gemI ) {
                                wxChar gemC = normColour.text[gemI];
                                if( gemC >= '0' && gemC <= '9' ) { gemDigit = (int)gemI; break; }
                            }
                            if( gemDigit != wxNOT_FOUND ) {
                                wxString gemSuffix = normColour.text.Mid(gemDigit);
                                bool gemNumericCsv = true;
                                for( size_t gemI = 0; gemI < gemSuffix.Length(); ++gemI ) {
                                    wxChar gemC = gemSuffix[gemI];
                                    if( !((gemC >= '0' && gemC <= '9') || gemC == ',' || gemC == ' ') ) {
                                        gemNumericCsv = false; break;
                                    }
                                }
                                if( gemNumericCsv ) {
                                    normColour.code = gemSuffix;
                                    normColour.code.Trim(true).Trim(false);
                                    normColour.text = normColour.text.Left(gemDigit);
                                    normColour.text.Trim(true).Trim(false);
                                }
                            }
                        }

                        candidatesJson << _T("      \"shape\": {\"raw\": \"")'''
if old not in chart: raise RuntimeError('+30 colour normalization anchor not found')
chart = chart.replace(old, new, 1)

# Add v3 metadata.
old = r'''                    candidatesJson << _T("  \"gem_format\": \"route-navigation-candidates-v3\",\n");
                    candidatesJson << _T("  \"candidates\": [\n");'''
new = r'''                    candidatesJson << _T("  \"gem_format\": \"route-navigation-candidates-v3\",\n");
                    candidatesJson << _T("  \"scanner_version\": \"GEM +30\",\n");
                    candidatesJson << wxString::Format(_T("  \"route_length_metres\": %.1f,\n"), routeLength);
                    candidatesJson << _T("  \"relevance_thresholds_metres\": {\"on_route\": 100, \"nearby\": 1000},\n");
                    candidatesJson << _T("  \"candidates\": [\n");'''
if old not in chart: raise RuntimeError('+30 header anchor not found')
chart = chart.replace(old, new, 1)

chart = chart.replace('GEMPROX +29', 'GEMPROX +30')
chart = chart.replace('GEMPOINT +29', 'GEMPOINT +30')
chart = chart.replace('GEMROUTE +29', 'GEMROUTE +30')
chart = chart.replace('GEMVIEW +29', 'GEMVIEW +30')
chart = chart.replace('GEMDIAG +29', 'GEMDIAG +30')
chart = chart.replace('GEMCANDIDATES +29', 'GEMCANDIDATES +30')
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

# +33A identity: +32 acquisition is unchanged; only candidate assembly
# deduplicates overlapping physical components and identical lights.
chart = chart.replace('GEM +32', 'GEM +33A')
chart = chart.replace('GEMPROX +32', 'GEMPROX +33A')
chart = chart.replace('GEMPOINT +32', 'GEMPOINT +33A')
chart = chart.replace('GEMROUTE +32', 'GEMROUTE +33A')
chart = chart.replace('GEMVIEW +32', 'GEMVIEW +33A')
chart = chart.replace('GEMDIAG +32', 'GEMDIAG +33A')
chart = chart.replace('GEMCANDIDATES +32', 'GEMCANDIDATES +33A')
chart = chart.replace(
    'GEMBUILD +33A full GPX route scalability test active',
    'GEMBUILD +33A overlap deduplication active'
)
chart = chart.replace('GEMBUILD +32 production candidate output active',
                      'GEMBUILD +32 full GPX route scalability test active')

# +33A.1: candidate-level source-chart provenance.
chart = chart.replace('GEM +33A', 'GEM +33A.1')
chart = chart.replace('GEMPROX +33A', 'GEMPROX +33A.1')
chart = chart.replace('GEMPOINT +33A', 'GEMPOINT +33A.1')
chart = chart.replace('GEMROUTE +33A', 'GEMROUTE +33A.1')
chart = chart.replace('GEMVIEW +33A', 'GEMVIEW +33A.1')
chart = chart.replace('GEMDIAG +33A', 'GEMDIAG +33A.1')
chart = chart.replace('GEMCANDIDATES +33A', 'GEMCANDIDATES +33A.1')
chart = chart.replace(
    'GEMBUILD +33A.1 overlap deduplication active',
    'GEMBUILD +33A.1 overlap deduplication and chart provenance active'
)
# +33B: preserve extended LIGHTS semantics, including sectors.
chart = chart.replace('GEM +33A.1', 'GEM +33B')
chart = chart.replace('GEMPROX +33A.1', 'GEMPROX +33B')
chart = chart.replace('GEMPOINT +33A.1', 'GEMPOINT +33B')
chart = chart.replace('GEMROUTE +33A.1', 'GEMROUTE +33B')
chart = chart.replace('GEMVIEW +33A.1', 'GEMVIEW +33B')
chart = chart.replace('GEMDIAG +33A.1', 'GEMDIAG +33B')
chart = chart.replace('GEMCANDIDATES +33A.1', 'GEMCANDIDATES +33B')
chart = chart.replace(
    'GEMBUILD +33A.1 overlap deduplication and chart provenance active',
    'GEMBUILD +33B extended LIGHTS semantics active'
)
chart_path.write_text(chart, encoding="utf-8")

print("Patched", chart_path)
print("GEM +29: peer-chart PI_S57Obj geographic coordinates used directly")
print("GEM +29: point-object identity qualified by geographic position")
print("GEM +11: +9 selected-object export retained")
print("GEM +11: +10 corridor diagnostic retained")
print("GEM +33B: +33A.1 acquisition/provenance retained; extended LIGHTS semantics active")
print("GEM +18: normalized/raw navigation candidates -> gem-route-candidates-v2.json")
