#include "gemtest_pi.h"
extern "C" DECL_EXP opencpn_plugin* create_pi(void* ppimgr) { return new gemtest_pi(ppimgr); }
extern "C" DECL_EXP void destroy_pi(opencpn_plugin* p) { delete p; }
gemtest_pi::gemtest_pi(void* ppimgr) : opencpn_plugin_119(ppimgr), m_bitmap(32, 32) {}
int gemtest_pi::Init() {
    wxLogMessage("GEMTEST: plugin initialized; waiting for vector chart object info");
    return WANTS_VECTOR_CHART_OBJECT_INFO;
}
bool gemtest_pi::DeInit() { wxLogMessage("GEMTEST: plugin deinitialized"); return true; }
int gemtest_pi::GetAPIVersionMajor() { return 1; }
int gemtest_pi::GetAPIVersionMinor() { return 19; }
int gemtest_pi::GetPlugInVersionMajor() { return 0; }
int gemtest_pi::GetPlugInVersionMinor() { return 1; }
wxBitmap* gemtest_pi::GetPlugInBitmap() { return &m_bitmap; }
wxString gemtest_pi::GetCommonName() { return "GEM Test"; }
wxString gemtest_pi::GetShortDescription() { return "Tests OpenCPN vector object callbacks for GEM Marine."; }
wxString gemtest_pi::GetLongDescription() { return "Diagnostic-only plugin. Logs vector chart object information supplied by OpenCPN."; }
void gemtest_pi::SendVectorChartObjectInfo(wxString& chart, wxString& feature, wxString& objname,
                                           double lat, double lon, double scale, int nativescale) {
    wxLogMessage("GEMTEST OBJECT RECEIVED");
    wxLogMessage("GEMTEST Chart: %s", chart);
    wxLogMessage("GEMTEST Feature: %s", feature);
    wxLogMessage("GEMTEST Name: %s", objname);
    wxLogMessage("GEMTEST Latitude: %.8f", lat);
    wxLogMessage("GEMTEST Longitude: %.8f", lon);
    wxLogMessage("GEMTEST Display scale: %.2f", scale);
    wxLogMessage("GEMTEST Native scale: %d", nativescale);
}
