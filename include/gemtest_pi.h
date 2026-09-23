#ifndef GEMTEST_PI_H
#define GEMTEST_PI_H
#include "wx/wxprec.h"
#ifndef WX_PRECOMP
#include "wx/wx.h"
#endif
#include "ocpn_plugin.h"
class gemtest_pi : public opencpn_plugin_119 {
public:
    explicit gemtest_pi(void* ppimgr);
    int Init() override;
    bool DeInit() override;
    int GetAPIVersionMajor() override;
    int GetAPIVersionMinor() override;
    int GetPlugInVersionMajor() override;
    int GetPlugInVersionMinor() override;
    wxBitmap* GetPlugInBitmap() override;
    wxString GetCommonName() override;
    wxString GetShortDescription() override;
    wxString GetLongDescription() override;
    void SendVectorChartObjectInfo(wxString& chart, wxString& feature, wxString& objname,
                                   double lat, double lon, double scale, int nativescale) override;
private:
    wxBitmap m_bitmap;
};
#endif
