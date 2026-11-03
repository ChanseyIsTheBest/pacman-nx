/**
 * @file    gpu/d3d/hooks/state.cpp
 * @brief   N&B's D3D state calls, hooked with the native ports (d3d_native.h).
 *
 * The render and sampler state setters are the ones N&B's state tables name
 * (D3D::InitializeApiState puts them into every device's dispatch table,
 * which the game's inline SetRenderState / SetSamplerState call through).
 * The rest are D3DDevice_Set* and the CDevice internals that write the ring.
 */
#include <cstring>

#include <rex/hook.h>

#include "renut_engine/gpu/banjo_renut_select.h"
#include <rex/types.h>

#include "renut_engine/gpu/d3d/d3d_native.h"
#include "renut_engine/gpu/guest/guest_memory.h"

using namespace renut::gpu;

namespace {

template <u32 State>
void SetRenderStateHook(u32 device, u32 value) {
  native::SetRenderState(native::DeviceAt(device), State, value);
}

template <u32 State>
void SetSamplerStateHook(u32 device, u32 sampler, u32 value) {
  native::SetSamplerState(native::DeviceAt(device), sampler, State, value);
}

template <u32 State>
u32 GetRenderStateHook(u32 device) {
  return native::GetRenderState(native::DeviceAt(device), State);
}

template <u32 State>
u32 GetSamplerStateHook(u32 device, u32 sampler) {
  return native::GetSamplerState(native::DeviceAt(device), sampler, State);
}

// The device's AddRef of a resource it hands out (D3DResource_AddRef,
// resource.cpp).
u32 AddRefResource(u32 resource) {
  return native::AddRefResource(resource);
}

// D3DSurface *GetRenderTarget(D3DDevice*, DWORD Index) [0x82636ED0]
u32 D3DDevice_GetRenderTarget_hook(u32 device, u32 index) {
  const native::Device d = native::DeviceAt(device);
  const u32 surface = d && index < 4 ? d.W(native::off::RenderTargets + index * 4) : 0;
  if (surface)
    AddRefResource(surface);
  return surface;
}

// D3DSurface *GetDepthStencilSurface(D3DDevice*) [0x82636F10]
u32 D3DDevice_GetDepthStencilSurface_hook(u32 device) {
  const native::Device d = native::DeviceAt(device);
  const u32 surface = d ? d.W(native::off::DepthStencil) : 0;
  if (surface)
    AddRefResource(surface);
  return surface;
}

// D3DVertexBuffer *GetStreamSource(D3DDevice*, UINT StreamNumber,
//     UINT *pOffsetInBytes, UINT *pStride) [0x82636E40]: the offset is the
// stream's fetch constant address less the buffer's.
u32 D3DDevice_GetStreamSource_hook(u32 device, u32 stream, mapped_u32 offset, mapped_u32 stride) {
  const native::Device d = native::DeviceAt(device);
  if (!d || stream >= 16)
    return 0;
  const u32 buffer = d.W(native::off::StreamSources + stream * 4);
  u32 bytes = 0;
  if (buffer) {
    const u32 fetch = d.W(native::off::TextureFetch + (95 - stream) * 8);
    bytes = fetch - native::GpuAddress(GuestPtr<const be_u32>(buffer)[6]);
    AddRefResource(buffer);
  }
  if (offset)
    *offset = bytes;
  if (stride)
    *stride = u32(d.B(native::off::StreamStrides + stream)) << 2;
  return buffer;
}

// void D3DDevice_GetViewport(D3DDevice*, D3DVIEWPORT9*) [0x82244B18]
void D3DDevice_GetViewport_hook(u32 device, mapped_u32 viewport) {
  const native::Device d = native::DeviceAt(device);
  if (!d || !viewport)
    return;
  for (u32 i = 0; i < 4; ++i)  // fctidz, the low word
    viewport[i] = u32(native::TruncateToI64(d.F(0x32E0 + i * 4)));  // katamari-nx: 0x3170->0x3160 (pacman-nx: 0x3160->0x3218) (tu3: 0x3218->0x32E0)
  viewport[4] = d.W(0x32F0);  // katamari-nx: 0x3180->0x3170 (pacman-nx: 0x3170->0x3228) (tu3: 0x3228->0x32F0)
  viewport[5] = d.W(0x32F4);  // katamari-nx: 0x3184->0x3174 (pacman-nx: 0x3174->0x322C) (tu3: 0x322C->0x32F4)
}

// void D3DDevice_SetClipPlane(D3DDevice*, DWORD Index, const float *pPlane) [0x826370E8]
void D3DDevice_SetClipPlane_hook(u32 device, u32 index, mapped_u32 plane) {
  native::Device d = native::DeviceAt(device);
  if (!d || !plane || index >= 6)
    return;
  for (u32 i = 0; i < 4; ++i)
    d.SetW(0x2820 + index * 16 + i * 4, plane[i]);
  d.Dirty(4, u64(1) << (54 - index));
}

// void D3DDevice_SetVertexFetchConstant(D3DDevice*, UINT VertexFetchRegister,
//     D3DVertexBuffer*, UINT Offset) [0x82637138]: a vertex fetch slot of the
// 3 in a fetch constant, made a vertex fetch constant first.
void D3DDevice_SetVertexFetchConstant_hook(u32 device, u32 reg, u32 vertex_buffer, u32 offset) {
  native::Device d = native::DeviceAt(device);
  const auto *vb = vertex_buffer ? GuestPtr<const be_u32>(vertex_buffer) : nullptr;
  if (!d || !vb || reg > 0x5F)
    return;
  const u32 slot = (0x5F - reg) / 3;
  const u32 part = (0x5F - reg) - slot * 3;
  const u32 constant = native::off::TextureFetch + slot * 24;
  const u32 type = d.W(constant) & 3;
  if (type == 0 || type == 2)
    std::memset(d.bytes + constant, 0, 24);
  d.TouchRange(constant, 24);  // banjo-nx (2026-10-26, banjo_renut_tags)
  d.SetW(constant, native::Insert(d.W(constant), 1, 0, 2));
  d.Dirty(3, u64(1) << (31 - slot));
  d.SetW(constant + part * 8, native::GpuAddress(u32(vb[6]) + offset));
  d.SetW(constant + part * 8 + 4, native::Insert(u32(vb[7]) - offset, 1, 28, 2));
}

// The boolean and integer shader constants (D3DDevice_Set{Vertex,Pixel}
// ShaderConstant{B,I}): bits from 0x2780 (vertex) / 0x2790 (pixel), a word
// of x, y, z bytes each from 0x27A0 / 0x27E0.
void SetShaderConstantsB(u32 device, u32 base, u32 start, mapped_u32 data, u32 count) {
  native::Device d = native::DeviceAt(device);
  if (!d || !data)
    return;
  for (u32 i = 0; i < count; ++i, ++start) {
    const u32 word = base + (start >> 5) * 4;
    const u32 bit = 1u << (start & 31);
    d.SetW(word, (d.W(word) & ~bit) | ((u32(data[i]) & 1) << (start & 31)));
  }
  d.Dirty(4, u64(1) << 56);
}

void SetShaderConstantsI(u32 device, u32 base, u32 start, mapped_u32 data, u32 count) {
  native::Device d = native::DeviceAt(device);
  if (!d || !data)
    return;
  for (u32 i = 0; i < count; ++i) {
    const u32 x = u32(data[i * 4]) & 0xFF, y = u32(data[i * 4 + 1]) & 0xFF;
    const u32 z = u32(data[i * 4 + 2]) & 0xFF;
    d.SetW(base + (start + i) * 4, (z << 16) | (y << 8) | x);
  }
  d.Dirty(4, u64(1) << 56);
}

// void D3DDevice_SetVertexShaderConstantB(D3DDevice*, UINT StartRegister,
//     const BOOL*, UINT BoolCount) [0x821F0B40], and the others alike.
void D3DDevice_SetVertexShaderConstantB_hook(u32 device, u32 start, mapped_u32 data, u32 count) {
  SetShaderConstantsB(device, 0x2780, start, data, count);
}
void D3DDevice_SetPixelShaderConstantB_hook(u32 device, u32 start, mapped_u32 data, u32 count) {
  SetShaderConstantsB(device, 0x2790, start, data, count);
}
void D3DDevice_SetVertexShaderConstantI_hook(u32 device, u32 start, mapped_u32 data, u32 count) {
  SetShaderConstantsI(device, 0x27A0, start, data, count);
}
void D3DDevice_SetPixelShaderConstantI_hook(u32 device, u32 start, mapped_u32 data, u32 count) {
  SetShaderConstantsI(device, 0x27E0, start, data, count);
}

// void D3DDevice_EndIndexedVertices(D3DDevice*) [0x8263ED90]: the inline end
// of BeginIndexedVertices, back to the ring pointer it saved.
void D3DDevice_EndIndexedVertices_hook(u32 device) {
  native::Device d = native::DeviceAt(device);
  if (d)
    d.SetW(native::off::Ring, d.W(0x3614));  // katamari-nx: 0x3484->0x3474 (pacman-nx: 0x3474->0x3554) (tu3: 0x3554->0x3614)
}

// void D3DDevice_SetTexture(D3DDevice*, DWORD Sampler, D3DBaseTexture*,
//     UINT64 PendingMask3) [0x821FE558]; the mask is the sampler's fetch
// constant bit, which the port derives from Sampler.
void D3DDevice_SetTexture_hook(u32 device, u32 sampler, u32 texture) {
  native::SetTexture(native::DeviceAt(device), sampler, texture);
}

// void D3DDevice_SetStreamSource(D3DDevice*, UINT StreamNumber, D3DVertexBuffer*,
//     UINT OffsetInBytes, UINT Stride, UINT64 PendingMask3) [0x821F9438]
void D3DDevice_SetStreamSource_hook(u32 device, u32 stream, u32 vertex_buffer, u32 offset,
                                    u32 stride) {
  native::SetStreamSource(native::DeviceAt(device), stream, vertex_buffer, offset, stride);
}

// void D3DDevice_SetIndices(D3DDevice*, D3DIndexBuffer*) [0x821DE438]
void D3DDevice_SetIndices_hook(u32 device, u32 index_buffer) {
  native::SetIndices(native::DeviceAt(device), index_buffer);
}

// void D3DDevice_SetVertexDeclaration(D3DDevice*, D3DVertexDeclaration*) [0x821D5060]
void D3DDevice_SetVertexDeclaration_hook(u32 device, u32 declaration) {
  native::SetVertexDeclaration(native::DeviceAt(device), declaration);
}

// void D3DDevice_SetViewport(D3DDevice*, const D3DVIEWPORT9*) [0x821F2090]
void D3DDevice_SetViewport_hook(u32 device, u32 viewport) {
  native::SetViewport(native::DeviceAt(device), viewport);
}

// void D3D::SetViewport(D3DDevice*, float X, float Y, float Width, float Height,
//     float MinZ, float MaxZ) [0x821F2110]
void D3D_SetViewport_hook(u32 device, float x, float y, float width, float height, float min_z,
                          float max_z) {
  native::SetViewport(native::DeviceAt(device), x, y, width, height, min_z, max_z);
}

// void D3DDevice_SetScissorRect(D3DDevice*, const RECT*) [0x821F2368]
void D3DDevice_SetScissorRect_hook(u32 device, mapped_u32 rect) {
  if (!rect)
    return;
  native::SetScissorRect(native::DeviceAt(device), i32(u32(rect[0])), i32(u32(rect[1])),
                         i32(u32(rect[2])), i32(u32(rect[3])));
}

// void D3D::SetSurfaceClip(CDevice*, int, int, int, int) [0x821F2460]: the
// window scissor and per-tile clip packets, nothing else.
void D3D_SetSurfaceClip_hook(u32 /*device*/, u32, u32, u32, u32) {}

// void D3DDevice_SetRenderTarget(D3DDevice*, DWORD Index, D3DSurface*) [0x82248BD0]
void D3DDevice_SetRenderTarget_hook(u32 device, u32 index, u32 surface) {
  native::SetRenderTarget(native::DeviceAt(device), index, surface);
}

// void D3DDevice_SetDepthStencilSurface(D3DDevice*, D3DSurface*) [0x82248FB0]
void D3DDevice_SetDepthStencilSurface_hook(u32 device, u32 surface) {
  native::SetDepthStencilSurface(native::DeviceAt(device), surface);
}

// void D3D::SetSurfaceInfo(CDevice*, D3DSurface*) [0x82248F20]
void D3D_SetSurfaceInfo_hook(u32 device, u32 surface) {
  native::SetSurfaceInfo(native::DeviceAt(device), surface);
}

// void D3DDevice_SetPredication(D3DDevice*, DWORD PredicationMask) [0x821F9A48]
void D3DDevice_SetPredication_hook(u32 device, u32 mask) {
  native::SetPredication(native::DeviceAt(device), mask);
}

// void D3DDevice_SetCommandBufferPredication(D3DDevice*, DWORD TilePredication,
//     DWORD RunPredication) [0x826411C0]
void D3DDevice_SetCommandBufferPredication_hook(u32 device, u32 tile_predication,
                                                u32 run_predication) {
  native::SetCommandBufferPredication(native::DeviceAt(device), tile_predication,
                                      run_predication);
}

// void D3DDevice_SetShaderGPRAllocation(D3DDevice*, DWORD Flags,
//     DWORD VertexShaderCount, DWORD PixelShaderCount) [0x821EFD38]
void D3DDevice_SetShaderGPRAllocation_hook(u32 device, u32 flags, u32 vertex_count,
                                           u32 pixel_count) {
  native::SetShaderGPRAllocation(native::DeviceAt(device), flags, vertex_count, pixel_count);
}

// void D3D::CleanupGprAllocationSetup(CDevice*) [0x82637208]
void D3D_CleanupGprAllocationSetup_hook(u32 device) {
  native::CleanupGprAllocationSetup(native::DeviceAt(device));
}

// void D3DDevice_SetScreenExtentQueryMode(D3DDevice*, D3DSCREENEXTENTQUERYMODE)
// [0x826414C0]
void D3DDevice_SetScreenExtentQueryMode_hook(u32 device, u32 mode) {
  native::SetScreenExtentQueryMode(native::DeviceAt(device), mode);
}

// void D3DDevice_UnsetAll(D3DDevice*) [0x82634C10]
void D3DDevice_UnsetAll_hook(u32 device) {
  native::UnsetAll(native::DeviceAt(device));
}

// void D3D::ResetAllState(CDevice*, BOOL) [0x82255C98]
void D3D_ResetAllState_hook(u32 device, u32 /*skip_packets*/) {
  native::ResetAllState(native::DeviceAt(device));
}

// void D3D::InvalidateConstants(D3DDevice*) [0x82634B90]
void D3D_InvalidateConstants_hook(u32 device) {
  native::InvalidateConstants(native::DeviceAt(device));
}

// void D3DDevice_BlockUntilIdle(D3DDevice*) [0x82640010] (IDA: the second
// D3D::InvalidateConstants): waits for the device's current fence (N&B calls
// it before releasing a device).
void D3DDevice_BlockUntilIdle_hook(u32 device) {
  native::InvalidateConstantsAndWait(native::DeviceAt(device));
}

} // namespace

// Render states, by their index in N&B's table (off_82E506F0).
BANJO_RENUT_HOOK(sub_8222AFE8, SetRenderStateHook<10>);  // pacman-nx: Katamari sub_824DC2F8, N&B sub_82635740; KAT,NB (base sub_821B6570)
BANJO_RENUT_HOOK(sub_8222B058, SetRenderStateHook<11>);  // pacman-nx: Katamari sub_824DC368, N&B sub_821CB040; KAT,NB (base sub_821B65E0)
BANJO_RENUT_HOOK(sub_8222B028, SetRenderStateHook<12>);  // pacman-nx: Katamari sub_824DC338, N&B sub_82635780; KAT,NB (base sub_821B65B0)
BANJO_RENUT_HOOK(sub_8222A8F0, SetRenderStateHook<13>);  // pacman-nx: Katamari sub_824DBBD8, N&B sub_8225D148; KAT,NB (base sub_821B5E78)
BANJO_RENUT_HOOK(sub_8222A8C0, SetRenderStateHook<14>);  // pacman-nx: Katamari sub_824DBBA8, N&B sub_8225D168; KAT,NB (base sub_821B5E48)
BANJO_RENUT_HOOK(sub_8222A958, SetRenderStateHook<15>);  // pacman-nx: Katamari sub_824DBC40, N&B sub_821F9748; KAT,NB (base sub_821B5EE0)
BANJO_RENUT_HOOK(sub_8222ACE8, SetRenderStateHook<16>);  // pacman-nx: Katamari sub_824DBFD0, N&B sub_821F96C0; KAT,NB (base sub_821B6270)
BANJO_RENUT_HOOK(sub_8222AE10, SetRenderStateHook<17>);  // pacman-nx: Katamari sub_824DC100, N&B sub_8223D118; KAT,NB (base sub_821B6398)
BANJO_RENUT_HOOK(sub_8222AA78, SetRenderStateHook<18>);  // pacman-nx: Katamari sub_824DBD60, N&B sub_821FF1D0; KAT,NB (base sub_821B6000)
BANJO_RENUT_HOOK(sub_8222AB08, SetRenderStateHook<19>);  // pacman-nx: Katamari sub_824DBDF0, N&B sub_821FF8D8; KAT,NB (base sub_821B6090)
BANJO_RENUT_HOOK(sub_8222A9E8, SetRenderStateHook<20>);  // pacman-nx: Katamari sub_824DBCD0, N&B sub_821F54F0; KAT,NB (base sub_821B5F70)
BANJO_RENUT_HOOK(sub_8222AC08, SetRenderStateHook<21>);  // pacman-nx: Katamari sub_824DBEF0, N&B sub_82235CD8; KAT,NB (base sub_821B6190)
BANJO_RENUT_HOOK(sub_8222AC78, SetRenderStateHook<22>);  // pacman-nx: Katamari sub_824DBF60, N&B sub_821EFB00; KAT,NB (base sub_821B6200)
BANJO_RENUT_HOOK(sub_8222AB98, SetRenderStateHook<23>);  // pacman-nx: Katamari sub_824DBE80, N&B sub_821EE830; KAT,NB (base sub_821B6120)
BANJO_RENUT_HOOK(sub_8222A920, SetRenderStateHook<24>);  // pacman-nx: Katamari sub_824DBC08, N&B sub_82635498; KAT,NB (base sub_821B5EA8)
BANJO_RENUT_HOOK(sub_8222AD80, SetRenderStateHook<25>);  // pacman-nx: Katamari sub_824DC068, N&B sub_82635550; KAT,NB (base sub_821B6308)
BANJO_RENUT_HOOK(sub_8222ADE0, SetRenderStateHook<26>);  // pacman-nx: Katamari sub_824DC0D0, N&B sub_826355B8; KAT,NB (base sub_821B6368)
BANJO_RENUT_HOOK(sub_8222B090, SetRenderStateHook<27>);  // pacman-nx: Katamari sub_824DC3A0, N&B sub_826357C0; KAT,NB (base sub_821B6618)
BANJO_RENUT_HOOK(sub_8222B0D0, SetRenderStateHook<28>);  // pacman-nx: Katamari sub_824DC3E0, N&B sub_82635800; KAT,NB (base sub_821B6658)
BANJO_RENUT_HOOK(sub_8222B138, SetRenderStateHook<29>);  // pacman-nx: Katamari sub_824DC448, N&B sub_82635868; KAT,NB (base sub_821B66C0)
BANJO_RENUT_HOOK(sub_8222B170, SetRenderStateHook<30>);  // pacman-nx: Katamari sub_824DC480, N&B sub_826358A0; KAT,NB (base sub_821B66F8)
BANJO_RENUT_HOOK(sub_8222B1A8, SetRenderStateHook<31>);  // pacman-nx: Katamari sub_824DC4B8, N&B sub_826358D8; KAT,NB (base sub_821B6730)
BANJO_RENUT_HOOK(sub_8222B108, SetRenderStateHook<32>);  // pacman-nx: Katamari sub_824DC418, N&B sub_82635838; KAT,NB (base sub_821B6690)
BANJO_RENUT_HOOK(sub_8222B2A8, SetRenderStateHook<33>);  // pacman-nx: Katamari sub_824DC5B8, N&B sub_826359D8; KAT,NB (base sub_821B6830)
BANJO_RENUT_HOOK(sub_8222B2C8, SetRenderStateHook<34>);  // pacman-nx: Katamari sub_824DC5D8, N&B sub_826359F8; KAT,NB (base sub_821B6850)
BANJO_RENUT_HOOK(sub_8222B2E8, SetRenderStateHook<35>);  // pacman-nx: Katamari sub_824DC5F8, N&B sub_82635A18; KAT,NB (base sub_821B6870)
BANJO_RENUT_HOOK(sub_8222B208, SetRenderStateHook<36>);  // pacman-nx: Katamari sub_824DC518, N&B sub_82635938; KAT,NB (base sub_821B6790)
BANJO_RENUT_HOOK(sub_8222B240, SetRenderStateHook<37>);  // pacman-nx: Katamari sub_824DC550, N&B sub_82635970; KAT,NB (base sub_821B67C8)
BANJO_RENUT_HOOK(sub_8222B278, SetRenderStateHook<38>);  // pacman-nx: Katamari sub_824DC588, N&B sub_826359A8; KAT,NB (base sub_821B6800)
BANJO_RENUT_HOOK(sub_8222B1D8, SetRenderStateHook<39>);  // pacman-nx: Katamari sub_824DC4E8, N&B sub_82635908; KAT,NB (base sub_821B6760)
BANJO_RENUT_HOOK(sub_8222B308, SetRenderStateHook<40>);  // pacman-nx: Katamari sub_824DC618, N&B sub_82635A38; KAT,NB (base sub_821B6890)
BANJO_RENUT_HOOK(sub_8222B328, SetRenderStateHook<41>);  // pacman-nx: Katamari sub_824DC638, N&B sub_82635A58; KAT,NB (base sub_821B68B0)
BANJO_RENUT_HOOK(sub_8222B348, SetRenderStateHook<42>);  // pacman-nx: Katamari sub_824DC658, N&B sub_82635A78; KAT,NB (base sub_821B68D0)
BANJO_RENUT_HOOK(sub_8222B368, SetRenderStateHook<43>);  // pacman-nx: Katamari sub_824DC678, N&B sub_8225D188; KAT,NB (base sub_821B68F0)
BANJO_RENUT_HOOK(sub_8222B698, SetRenderStateHook<44>);  // pacman-nx: Katamari sub_824DC9A0, N&B sub_82635CC0; KAT,NB (base sub_821B6C20)
BANJO_RENUT_HOOK(sub_8222B6F0, SetRenderStateHook<45>);  // pacman-nx: Katamari sub_824DCA00, N&B sub_82635D20; KAT,NB (base sub_821B6C78)
BANJO_RENUT_HOOK(sub_8222B688, SetRenderStateHook<46>);  // pacman-nx: Katamari sub_824DC990, N&B sub_82635CB0; KAT,NB (base sub_821B6C10)
BANJO_RENUT_HOOK(sub_8222B740, SetRenderStateHook<47>);  // pacman-nx: Katamari sub_824DCA58, N&B sub_822371C0; KAT,NB (base sub_821B6CC8)
BANJO_RENUT_HOOK(sub_8222B538, SetRenderStateHook<48>);  // pacman-nx: Katamari sub_824DC840, N&B sub_82635B98; KAT,NB (base sub_821B6AC0)
BANJO_RENUT_HOOK(sub_8222B568, SetRenderStateHook<49>);  // pacman-nx: Katamari sub_824DC870, N&B sub_82635BC8; KAT,NB (base sub_821B6AF0)
BANJO_RENUT_HOOK(sub_8222D480, SetRenderStateHook<50>);  // pacman-nx: Katamari sub_824DE720, N&B sub_82635AA8; KAT,NB (base sub_821B89D8)
BANJO_RENUT_HOOK(sub_8222B3C8, SetRenderStateHook<51>);  // pacman-nx: Katamari sub_824DC6D0, N&B sub_82635AC0; KAT,NB (base sub_821B6950)
BANJO_RENUT_HOOK(sub_8222B490, SetRenderStateHook<52>);  // pacman-nx: Katamari sub_824DC798, N&B sub_821CAFA8; KAT,NB (base sub_821B6A18)
BANJO_RENUT_HOOK(sub_8222B588, SetRenderStateHook<53>);  // pacman-nx: Katamari sub_824DC890, N&B sub_821CAF70; KAT,NB (base sub_821B6B10)
BANJO_RENUT_HOOK(sub_8222B5C8, SetRenderStateHook<54>);  // pacman-nx: Katamari sub_824DC8D0, N&B sub_82635BF0; KAT,NB (base sub_821B6B50)
BANJO_RENUT_HOOK(sub_8222B608, SetRenderStateHook<55>);  // pacman-nx: Katamari sub_824DC910, N&B sub_82635C30; KAT,NB (base sub_821B6B90)
BANJO_RENUT_HOOK(sub_8222B648, SetRenderStateHook<56>);  // pacman-nx: Katamari sub_824DC950, N&B sub_82635C70; KAT,NB (base sub_821B6BD0)
BANJO_RENUT_HOOK(sub_8222BE10, SetRenderStateHook<57>);  // pacman-nx: Katamari sub_824DD190, N&B sub_826363C8; KAT,NB (base sub_821B7398)
BANJO_RENUT_HOOK(sub_8222BDA0, SetRenderStateHook<58>);  // pacman-nx: Katamari sub_824DD120, N&B sub_82636358; KAT,NB (base sub_821B7328)
BANJO_RENUT_HOOK(sub_8222BDD8, SetRenderStateHook<59>);  // pacman-nx: Katamari sub_824DD158, N&B sub_82636390; KAT,NB (base sub_821B7360)
BANJO_RENUT_HOOK(sub_8222B790, SetRenderStateHook<60>);  // pacman-nx: Katamari sub_824DCAB0, N&B sub_82635D88; KAT,NB (base sub_821B6D18)
BANJO_RENUT_HOOK(sub_8222B7B0, SetRenderStateHook<61>);  // pacman-nx: Katamari sub_824DCAD0, N&B sub_82635DA8; KAT,NB (base sub_821B6D38)
BANJO_RENUT_HOOK(sub_8222B7D8, SetRenderStateHook<62>);  // pacman-nx: Katamari sub_824DCAF8, N&B sub_82635DD0; KAT,NB (base sub_821B6D60)
BANJO_RENUT_HOOK(sub_8222B800, SetRenderStateHook<63>);  // pacman-nx: Katamari sub_824DCB20, N&B sub_82635DF8; KAT,NB (base sub_821B6D88)
BANJO_RENUT_HOOK(sub_8222B828, SetRenderStateHook<64>);  // pacman-nx: Katamari sub_824DCB48, N&B sub_82635E20; KAT,NB (base sub_821B6DB0)
BANJO_RENUT_HOOK(sub_8222B850, SetRenderStateHook<65>);  // pacman-nx: Katamari sub_824DCB70, N&B sub_82635E48; KAT,NB (base sub_821B6DD8)
BANJO_RENUT_HOOK(sub_8222B878, SetRenderStateHook<66>);  // pacman-nx: Katamari sub_824DCB98, N&B sub_82635E70; KAT,NB (base sub_821B6E00)
BANJO_RENUT_HOOK(sub_8222B8A0, SetRenderStateHook<67>);  // pacman-nx: Katamari sub_824DCBC0, N&B sub_82635E98; KAT,NB (base sub_821B6E28)
BANJO_RENUT_HOOK(sub_8222B8C0, SetRenderStateHook<68>);  // pacman-nx: Katamari sub_824DCBE0, N&B sub_82635EB8; KAT,NB (base sub_821B6E48)
BANJO_RENUT_HOOK(sub_8222B8E0, SetRenderStateHook<69>);  // pacman-nx: Katamari sub_824DCC00, N&B sub_82635ED8; KAT,NB (base sub_821B6E68)
BANJO_RENUT_HOOK(sub_8222B908, SetRenderStateHook<70>);  // pacman-nx: Katamari sub_824DCC28, N&B sub_82635F00; KAT,NB (base sub_821B6E90)
BANJO_RENUT_HOOK(sub_8222B930, SetRenderStateHook<71>);  // pacman-nx: Katamari sub_824DCC50, N&B sub_82635F28; KAT,NB (base sub_821B6EB8)
BANJO_RENUT_HOOK(sub_8222B958, SetRenderStateHook<72>);  // pacman-nx: Katamari sub_824DCC78, N&B sub_82635F50; KAT,NB (base sub_821B6EE0)
BANJO_RENUT_HOOK(sub_8222B980, SetRenderStateHook<73>);  // pacman-nx: Katamari sub_824DCCA0, N&B sub_82635F78; KAT,NB (base sub_821B6F08)
BANJO_RENUT_HOOK(sub_8222B9A8, SetRenderStateHook<74>);  // pacman-nx: Katamari sub_824DCCC8, N&B sub_82635FA0; KAT,NB (base sub_821B6F30)
BANJO_RENUT_HOOK(sub_8222B9D0, SetRenderStateHook<75>);  // pacman-nx: Katamari sub_824DCCF0, N&B sub_82635FC8; KAT,NB (base sub_821B6F58)
BANJO_RENUT_HOOK(sub_8222BAF0, SetRenderStateHook<76>);  // pacman-nx: Katamari sub_824DCE10, N&B sub_821D53E8; KAT,NB (base sub_821B7078)
BANJO_RENUT_HOOK(sub_8222BB40, SetRenderStateHook<77>);  // pacman-nx: Katamari sub_824DCE60, N&B sub_826360F8; KAT,NB (base sub_821B70C8)
BANJO_RENUT_HOOK(sub_8222BBD8, SetRenderStateHook<78>);  // pacman-nx: Katamari sub_824DCF10, N&B sub_82636190; KAT,NB (base sub_821B7160)
BANJO_RENUT_HOOK(sub_8222BC70, SetRenderStateHook<79>);  // pacman-nx: Katamari sub_824DCFC0, N&B sub_82636228; KAT,NB (base sub_821B71F8)
BANJO_RENUT_HOOK(sub_8222BD08, SetRenderStateHook<80>);  // pacman-nx: Katamari sub_824DD070, N&B sub_826362C0; KAT,NB (base sub_821B7290)
BANJO_RENUT_HOOK(sub_8222BE48, SetRenderStateHook<81>);  // pacman-nx: Katamari sub_824DD1C8, N&B sub_82636400; KAT,NB (base sub_821B73D0)
BANJO_RENUT_HOOK(sub_8222BE80, SetRenderStateHook<82>);  // pacman-nx: Katamari sub_824DD200, N&B sub_82636438; KAT,NB (base sub_821B7408)
BANJO_RENUT_HOOK(sub_8222BEB0, SetRenderStateHook<83>);  // pacman-nx: Katamari sub_824DD230, N&B sub_82636468; KAT,NB (base sub_821B7438)
BANJO_RENUT_HOOK(sub_8222BED8, SetRenderStateHook<84>);  // pacman-nx: Katamari sub_824DD258, N&B sub_82636490; KAT,NB (base sub_821B7460)
BANJO_RENUT_HOOK(sub_8222BF08, SetRenderStateHook<85>);  // pacman-nx: Katamari sub_824DD288, N&B sub_826364C0; KAT,NB (base sub_821B7490)
BANJO_RENUT_HOOK(sub_8222BF30, SetRenderStateHook<86>);  // pacman-nx: Katamari sub_824DD2C0, N&B sub_826364E8; KAT,NB (base sub_821B74B8)
BANJO_RENUT_HOOK(sub_8222BF60, SetRenderStateHook<87>);  // pacman-nx: Katamari sub_824DD2F0, N&B sub_82636518; KAT,NB (base sub_821B74E8)
BANJO_RENUT_HOOK(sub_8222BF90, SetRenderStateHook<88>);  // pacman-nx: Katamari sub_824DD320, N&B sub_82636548; KAT,NB (base sub_821B7518)
BANJO_RENUT_HOOK(sub_8222BFB8, SetRenderStateHook<89>);  // pacman-nx: Katamari sub_824DD348, N&B sub_82636570; KAT,NB (base sub_821B7540)
BANJO_RENUT_HOOK(sub_8222C080, SetRenderStateHook<90>);  // pacman-nx: Katamari sub_824DD410, N&B sub_826365E0; KAT,NB (base sub_821B7608)
BANJO_RENUT_HOOK(sub_8222C0B0, SetRenderStateHook<91>);  // pacman-nx: Katamari sub_824DD440, N&B sub_82636610; KAT,NB (base sub_821B7638)
BANJO_RENUT_HOOK(sub_8222C0E0, SetRenderStateHook<92>);  // pacman-nx: Katamari sub_824DD470, N&B sub_82636640; KAT,NB (base sub_821B7668)
BANJO_RENUT_HOOK(sub_8222C110, SetRenderStateHook<93>);  // pacman-nx: Katamari sub_824DD4A0, N&B sub_82636670; KAT,NB (base sub_821B7698)
BANJO_RENUT_HOOK(sub_8222C130, SetRenderStateHook<94>);  // pacman-nx: Katamari sub_824DD4C0, N&B sub_82636690; KAT,NB (base sub_821B76B8)
BANJO_RENUT_HOOK(sub_8222C140, SetRenderStateHook<95>);  // pacman-nx: Katamari sub_824DD4D0, N&B sub_826366A0; KAT,NB (base sub_821B76C8)
BANJO_RENUT_HOOK(sub_8222BFE8, SetRenderStateHook<96>);  // pacman-nx: Katamari sub_824DD378, N&B sub_826365A0; KAT,NB (base sub_821B7570)
BANJO_RENUT_HOOK(sub_8222C018, SetRenderStateHook<97>);  // pacman-nx: Katamari sub_824DD3A8, N&B sub_82257938; KAT,NB (base sub_821B75A0)
BANJO_RENUT_HOOK(sub_8222AF10, SetRenderStateHook<98>);  // pacman-nx: Katamari sub_824DC220, N&B sub_82635660; KAT,NB (base sub_821B6498)
BANJO_RENUT_HOOK(sub_8222AF48, SetRenderStateHook<99>);  // pacman-nx: Katamari sub_824DC258, N&B sub_82635698; KAT,NB (base sub_821B64D0)
BANJO_RENUT_HOOK(sub_8222AFB8, SetRenderStateHook<100>);  // pacman-nx: Katamari sub_824DC2C8, N&B sub_82635710; KAT,NB (base sub_821B6540)

// Sampler states, by their index in N&B's table (off_82E50BD0).
BANJO_RENUT_HOOK(sub_8222C8D8, SetSamplerStateHook<0>);  // pacman-nx: Katamari sub_824DDC30, N&B sub_8224B2C0; KAT,NB (base sub_821B7E60)
BANJO_RENUT_HOOK(sub_8222C928, SetSamplerStateHook<1>);  // pacman-nx: Katamari sub_824DDC80, N&B sub_821DB8C8; KAT,NB (base sub_821B7EB0)
BANJO_RENUT_HOOK(sub_8222C978, SetSamplerStateHook<2>);  // pacman-nx: Katamari sub_824DDCD0, N&B sub_82636C30; KAT,NB (base sub_821B7F00)
BANJO_RENUT_HOOK(sub_8222C868, SetSamplerStateHook<3>);  // pacman-nx: Katamari sub_824DDBC0, N&B sub_82636B90; KAT,NB (base sub_821B7DF0)
BANJO_RENUT_HOOK(sub_8222C308, SetSamplerStateHook<4>);  // pacman-nx: Katamari sub_824DD680, N&B sub_821FE308; KAT,NB (base sub_821B7890)
BANJO_RENUT_HOOK(sub_8222C160, SetSamplerStateHook<5>);  // pacman-nx: Katamari sub_824DD4F0, N&B sub_821FE3D0; KAT,NB (base sub_821B76E8)
BANJO_RENUT_HOOK(sub_8222C4A8, SetSamplerStateHook<6>);  // pacman-nx: Katamari sub_824DD810, N&B sub_8225D108; KAT,NB (base sub_821B7A30)
BANJO_RENUT_HOOK(sub_8222C6C8, SetSamplerStateHook<7>);  // pacman-nx: Katamari sub_824DDA20, N&B sub_82636A58; KAT,NB (base sub_821B7C50)
BANJO_RENUT_HOOK(sub_8222C768, SetSamplerStateHook<8>);  // pacman-nx: Katamari sub_824DDAC0, N&B sub_821FE6D8; KAT,NB (base sub_821B7CF0)
BANJO_RENUT_HOOK(sub_8222C5A8, SetSamplerStateHook<9>);  // pacman-nx: Katamari sub_824DD900, N&B sub_82636938; KAT,NB (base sub_821B7B30)
BANJO_RENUT_HOOK(sub_8222C408, SetSamplerStateHook<10>);  // pacman-nx: Katamari sub_824DD778, N&B sub_826367D8; KAT,NB (base sub_821B7990)
BANJO_RENUT_HOOK(sub_8222C260, SetSamplerStateHook<11>);  // pacman-nx: Katamari sub_824DD5E8, N&B sub_826366F8; KAT,NB (base sub_821B77E8)
BANJO_RENUT_HOOK(sub_8222C500, SetSamplerStateHook<12>);  // pacman-nx: Katamari sub_824DD868, N&B sub_82636890; KAT,NB (base sub_821B7A88)
BANJO_RENUT_HOOK(sub_8222C7E8, SetSamplerStateHook<13>);  // pacman-nx: Katamari sub_824DDB40, N&B sub_82636B10; KAT,NB (base sub_821B7D70)
BANJO_RENUT_HOOK(sub_8222C9C8, SetSamplerStateHook<14>);  // pacman-nx: Katamari sub_824DDD20, N&B sub_82636C80; KAT,NB (base sub_821B7F50)
BANJO_RENUT_HOOK(sub_8222C620, SetSamplerStateHook<15>);  // pacman-nx: Katamari sub_824DD978, N&B sub_826369B0; KAT,NB (base sub_821B7BA8)
BANJO_RENUT_HOOK(sub_8222CA20, SetSamplerStateHook<16>);  // pacman-nx: Katamari sub_824DDD78, N&B sub_82636CD8; KAT,NB (base sub_821B7FA8)
BANJO_RENUT_HOOK(sub_8222CA78, SetSamplerStateHook<17>);  // pacman-nx: Katamari sub_824DDDD0, N&B sub_82636D30; KAT,NB (base sub_821B8000)
BANJO_RENUT_HOOK(sub_8222CAD0, SetSamplerStateHook<18>);  // pacman-nx: Katamari sub_824DDE28, N&B sub_82636D88; KAT,NB (base sub_821B8058)
BANJO_RENUT_HOOK(sub_8222CB28, SetSamplerStateHook<19>);  // pacman-nx: Katamari sub_824DDE80, N&B sub_82636DE0; KAT,NB (base sub_821B80B0)

BANJO_RENUT_HOOK(sub_82239378, D3DDevice_SetTexture_hook);  // pacman-nx: Katamari sub_824D2640, N&B sub_821FE558; GW,NB (base sub_821C42A0)
BANJO_RENUT_UNHOOKED_HOOK(unlinked_824A3D40, D3DDevice_SetTexture_hook);  // pacman-nx: Katamari sub_824A3D40, N&B sub_82BF2578; not in this game: D3DDevice_SetTexture_Inline: no match (an inline form in N&B)
BANJO_RENUT_HOOK(sub_8222CC80, D3DDevice_SetStreamSource_hook);  // pacman-nx: Katamari sub_824DDFE0, N&B sub_821F9438; GW,NB (base sub_821B8208)
BANJO_RENUT_HOOK(sub_8222CDA0, D3DDevice_SetIndices_hook);  // pacman-nx: Katamari sub_824DE188, N&B sub_821DE438; GW,NB (base sub_821B8328)
BANJO_RENUT_HOOK(sub_8222FD28, D3DDevice_SetVertexDeclaration_hook);  // pacman-nx: Katamari sub_824D4B48, N&B sub_821D5060; GW,KAT,NB (base sub_821BB1A8)
BANJO_RENUT_HOOK(sub_8222D490, D3DDevice_SetViewport_hook);  // pacman-nx: Katamari sub_824DE730, N&B sub_821F2090; GW (base sub_821B89E8)
BANJO_RENUT_HOOK(sub_8222D228, D3D_SetViewport_hook);  // pacman-nx: Katamari sub_824DE4B8, N&B sub_821F2110; GW,NB (base sub_821B8780)
BANJO_RENUT_HOOK(sub_8222CB88, D3DDevice_SetScissorRect_hook);  // pacman-nx: Katamari sub_824DDEE0, N&B sub_821F2368; GW,NB (base sub_821B8110)
BANJO_RENUT_HOOK(sub_8222A5D8, D3D_SetSurfaceClip_hook);  // pacman-nx: Katamari sub_824DB8C8, N&B sub_821F2460; GW,NB (base sub_821B5B58)
BANJO_RENUT_HOOK(sub_8222D5C0, D3DDevice_SetRenderTarget_hook);  // pacman-nx: Katamari sub_824DE868, N&B sub_82248BD0; GW,NB (base sub_821B8B18)
BANJO_RENUT_HOOK(sub_8222D950, D3DDevice_SetDepthStencilSurface_hook);  // pacman-nx: Katamari sub_824DEBD0, N&B sub_82248FB0; GW,NB (base sub_821B8E68)
BANJO_RENUT_HOOK(sub_8222D530, D3D_SetSurfaceInfo_hook);  // pacman-nx: Katamari sub_824DE7D0, N&B sub_82248F20; GW,NB (base sub_821B8A88)
BANJO_RENUT_HOOK(sub_82246C70, D3DDevice_SetPredication_hook);  // pacman-nx: Katamari sub_824EFA58, N&B sub_821F9A48; GW,NB (base sub_821CFFB0)
BANJO_RENUT_UNHOOKED_HOOK_SHARED(unlinked_826411C0, D3DDevice_SetCommandBufferPredication_hook);  // pacman-nx: N&B sub_826411C0; not in this game: D3DDevice_SetCommandBufferPredication: no command buffers; SetPredication sub_821CFFB0 is 
BANJO_RENUT_HOOK(sub_8222FEB0, D3DDevice_SetShaderGPRAllocation_hook);  // pacman-nx: Katamari sub_824D4CD8, N&B sub_821EFD38; GW (base sub_821BB330)
BANJO_RENUT_HOOK(sub_8222F3D8, D3D_CleanupGprAllocationSetup_hook);  // pacman-nx: Katamari sub_824D3FE0, N&B sub_82637208; GW,NB (base sub_821BA8E8)
BANJO_RENUT_HOOK(sub_822408D8, D3DDevice_SetScreenExtentQueryMode_hook);  // pacman-nx: Katamari sub_824E67C8, N&B sub_826414C0; GW,NB (base sub_821CA5C0)
BANJO_RENUT_HOOK(sub_82236D80, D3DDevice_UnsetAll_hook);  // pacman-nx: Katamari sub_824D0488, N&B sub_82634C10; GW,NB (base sub_821C1CD8)
BANJO_RENUT_HOOK(sub_8222D130, D3D_ResetAllState_hook);  // pacman-nx: Katamari sub_824DE3C0, N&B sub_82255C98; GW (base sub_821B8688)
BANJO_RENUT_UNHOOKED_HOOK_SHARED(unlinked_82634B90, D3D_InvalidateConstants_hook);  // pacman-nx: N&B sub_82634B90; not in this game: D3D_InvalidateConstants: ambiguous (0.86 / 0.81 in sub_821D0878 / sub_821D0608), left to t
BANJO_RENUT_HOOK(sub_8223F8E8, D3DDevice_BlockUntilIdle_hook);  // pacman-nx: Katamari sub_824E0518, N&B sub_82640010; HAND D3DDevice_BlockUntilIdle: Katamari's 30 instructions, reordered: BeginRing check, `li r10, (base sub_821C9650)
// Through a thunk (j_D3DDevice_SetRenderTarget 0x82636EC8).
BANJO_RENUT_UNHOOKED_HOOK(unlinked_82636EC8, D3DDevice_SetRenderTarget_hook);  // pacman-nx: N&B sub_82636EC8; not in this game: D3DDevice_SetRenderTarget_Thunk: no match; the game calls SetRenderTarget directly
BANJO_RENUT_UNHOOKED_HOOK(unlinked_82636ED0, D3DDevice_GetRenderTarget_hook);  // pacman-nx: N&B sub_82636ED0; not in this game: D3DDevice_GetRenderTarget: reads the device, left to the guest (tu3: still read by the game's own code, whose offsets are right)
BANJO_RENUT_UNHOOKED_HOOK(unlinked_82636F10, D3DDevice_GetDepthStencilSurface_hook);  // pacman-nx: N&B sub_82636F10; not in this game: D3DDevice_GetDepthStencilSurface: as above (tu3: still read by the game's own code, whose offsets are right)
BANJO_RENUT_UNHOOKED_HOOK(unlinked_82636E40, D3DDevice_GetStreamSource_hook);  // pacman-nx: N&B sub_82636E40; not in this game: D3DDevice_GetStreamSource: as above
BANJO_RENUT_UNHOOKED_HOOK(unlinked_82244B18, D3DDevice_GetViewport_hook);  // pacman-nx: N&B sub_82244B18; not in this game: D3DDevice_GetViewport: as above
BANJO_RENUT_HOOK(sub_8222D058, D3DDevice_SetClipPlane_hook);  // pacman-nx: N&B sub_826370E8; NB (base sub_821B85E0)
BANJO_RENUT_UNHOOKED_HOOK(unlinked_82637138, D3DDevice_SetVertexFetchConstant_hook);  // pacman-nx: N&B sub_82637138; not in this game: D3DDevice_SetVertexFetchConstant: no match
BANJO_RENUT_HOOK(sub_8222F710, D3DDevice_SetVertexShaderConstantB_hook);  // pacman-nx: Katamari sub_824D4470, N&B sub_821F0B40; HAND D3DDevice_SetVertexShaderConstantB: `addi r11,r11,2528` (the vertex bool block), called 3  (base sub_821BAC20)
BANJO_RENUT_HOOK(sub_8222F770, D3DDevice_SetPixelShaderConstantB_hook);  // pacman-nx: Katamari sub_824D44D0, N&B sub_82237208; HAND D3DDevice_SetPixelShaderConstantB: 2532, as N&B's sub_82237208 (base sub_821BAC80)
BANJO_RENUT_HOOK(sub_8222F7D0, D3DDevice_SetVertexShaderConstantI_hook);  // pacman-nx: N&B sub_826374B0; HAND D3DDevice_SetVertexShaderConstantI: `addi r10,r4,2535` as N&B's (base sub_821BACE0)
BANJO_RENUT_HOOK(sub_8222F828, D3DDevice_SetPixelShaderConstantI_hook);  // pacman-nx: N&B sub_82637500; HAND D3DDevice_SetPixelShaderConstantI: 2551 (base sub_821BAD38)
BANJO_RENUT_HOOK(sub_82235E30, D3DDevice_EndIndexedVertices_hook);  // pacman-nx: N&B sub_8263ED90; HAND D3DDevice_EndIndexedVertices: the same three instructions as N&B's: `lwz r11,13652(r3); st (base sub_821C1048)

// Render state getters, by their index in N&B's table (off_82E506F0, field 0).
BANJO_RENUT_HOOK(sub_8222B020, GetRenderStateHook<10>);  // pacman-nx: Katamari sub_824DC330, N&B sub_82635778; KAT,NB (base sub_821B65A8)
BANJO_RENUT_HOOK(sub_8222B080, GetRenderStateHook<11>);  // pacman-nx: Katamari sub_824DC390, N&B sub_826357B0; KAT,NB (base sub_821B6608)
BANJO_RENUT_HOOK(sub_8222B048, GetRenderStateHook<12>);  // pacman-nx: Katamari sub_824DC358, N&B sub_826357A0; KAT,NB (base sub_821B65D0)
BANJO_RENUT_HOOK(sub_8222A910, GetRenderStateHook<13>);  // pacman-nx: Katamari sub_824DBBF8, N&B sub_82635488; KAT,NB (base sub_821B5E98)
BANJO_RENUT_HOOK(sub_8222A8E0, GetRenderStateHook<14>);  // pacman-nx: Katamari sub_824DBBC8, N&B sub_82635478; KAT,NB (base sub_821B5E68)
BANJO_RENUT_HOOK(sub_8222A9D8, GetRenderStateHook<15>);  // pacman-nx: Katamari sub_824DBCC0, N&B sub_826354D0; KAT,NB (base sub_821B5F60)
BANJO_RENUT_HOOK(sub_8222AD70, GetRenderStateHook<16>);  // pacman-nx: Katamari sub_824DC058, N&B sub_82635540; KAT,NB (base sub_821B62F8)
BANJO_RENUT_HOOK(sub_8222AEA0, GetRenderStateHook<17>);  // pacman-nx: Katamari sub_824DC1A0, N&B sub_826355E8; KAT,NB (base sub_821B6428)
BANJO_RENUT_HOOK(sub_8222AAF8, GetRenderStateHook<18>);  // pacman-nx: Katamari sub_824DBDE0, N&B sub_826354F0; KAT,NB (base sub_821B6080)
BANJO_RENUT_HOOK(sub_8222AB88, GetRenderStateHook<19>);  // pacman-nx: Katamari sub_824DBE70, N&B sub_82635500; KAT,NB (base sub_821B6110)
BANJO_RENUT_HOOK(sub_8222AA68, GetRenderStateHook<20>);  // pacman-nx: Katamari sub_824DBD50, N&B sub_826354E0; KAT,NB (base sub_821B5FF0)
BANJO_RENUT_HOOK(sub_8222AC68, GetRenderStateHook<21>);  // pacman-nx: Katamari sub_824DBF50, N&B sub_82635520; KAT,NB (base sub_821B61F0)
BANJO_RENUT_HOOK(sub_8222ACD8, GetRenderStateHook<22>);  // pacman-nx: Katamari sub_824DBFC0, N&B sub_82635530; KAT,NB (base sub_821B6260)
BANJO_RENUT_HOOK(sub_8222ABF8, GetRenderStateHook<23>);  // pacman-nx: Katamari sub_824DBEE0, N&B sub_82635510; KAT,NB (base sub_821B6180)
BANJO_RENUT_HOOK(sub_8222A948, GetRenderStateHook<24>);  // pacman-nx: Katamari sub_824DBC30, N&B sub_826354C0; KAT,NB (base sub_821B5ED0)
BANJO_RENUT_HOOK(sub_8222ADB8, GetRenderStateHook<25>);  // pacman-nx: Katamari sub_824DC0A0, N&B sub_82635588; KAT,NB (base sub_821B6340)
BANJO_RENUT_HOOK(sub_8222AE00, GetRenderStateHook<26>);  // pacman-nx: Katamari sub_824DC0F0, N&B sub_826355D8; KAT,NB (base sub_821B6388)
BANJO_RENUT_HOOK(sub_8222B0C8, GetRenderStateHook<27>);  // pacman-nx: Katamari sub_824DC3D8, N&B sub_826357F8; KAT,NB (base sub_821B6650)
BANJO_RENUT_HOOK(sub_8222B0F8, GetRenderStateHook<28>);  // pacman-nx: Katamari sub_824DC408, N&B sub_82635828; KAT,NB (base sub_821B6680)
BANJO_RENUT_HOOK(sub_8222B160, GetRenderStateHook<29>);  // pacman-nx: Katamari sub_824DC470, N&B sub_82635890; KAT,NB (base sub_821B66E8)
BANJO_RENUT_HOOK(sub_8222B198, GetRenderStateHook<30>);  // pacman-nx: Katamari sub_824DC4A8, N&B sub_826358C8; KAT,NB (base sub_821B6720)
BANJO_RENUT_HOOK(sub_8222B1C8, GetRenderStateHook<31>);  // pacman-nx: Katamari sub_824DC4D8, N&B sub_826358F8; KAT,NB (base sub_821B6750)
BANJO_RENUT_HOOK(sub_8222B128, GetRenderStateHook<32>);  // pacman-nx: Katamari sub_824DC438, N&B sub_82635858; KAT,NB (base sub_821B66B0)
BANJO_RENUT_HOOK(sub_8222B2C0, GetRenderStateHook<33>);  // pacman-nx: Katamari sub_824DC5D0, N&B sub_826359F0; KAT,NB (base sub_821B6848)
BANJO_RENUT_HOOK(sub_8222B2E0, GetRenderStateHook<34>);  // pacman-nx: Katamari sub_824DC5F0, N&B sub_82635A10; KAT,NB (base sub_821B6868)
BANJO_RENUT_HOOK(sub_8222B300, GetRenderStateHook<35>);  // pacman-nx: Katamari sub_824DC610, N&B sub_82635A30; KAT,NB (base sub_821B6888)
BANJO_RENUT_HOOK(sub_8222B230, GetRenderStateHook<36>);  // pacman-nx: Katamari sub_824DC540, N&B sub_82635960; KAT,NB (base sub_821B67B8)
BANJO_RENUT_HOOK(sub_8222B268, GetRenderStateHook<37>);  // pacman-nx: Katamari sub_824DC578, N&B sub_82635998; KAT,NB (base sub_821B67F0)
BANJO_RENUT_HOOK(sub_8222B298, GetRenderStateHook<38>);  // pacman-nx: Katamari sub_824DC5A8, N&B sub_826359C8; KAT,NB (base sub_821B6820)
BANJO_RENUT_HOOK(sub_8222B1F8, GetRenderStateHook<39>);  // pacman-nx: Katamari sub_824DC508, N&B sub_82635928; KAT,NB (base sub_821B6780)
BANJO_RENUT_HOOK(sub_8222B320, GetRenderStateHook<40>);  // pacman-nx: Katamari sub_824DC630, N&B sub_82635A50; KAT,NB (base sub_821B68A8)
BANJO_RENUT_HOOK(sub_8222B340, GetRenderStateHook<41>);  // pacman-nx: Katamari sub_824DC650, N&B sub_82635A70; KAT,NB (base sub_821B68C8)
BANJO_RENUT_HOOK(sub_8222B360, GetRenderStateHook<42>);  // pacman-nx: Katamari sub_824DC670, N&B sub_82635A90; KAT,NB (base sub_821B68E8)
BANJO_RENUT_HOOK(sub_8222B3B0, GetRenderStateHook<43>);  // pacman-nx: Katamari sub_824DC6B8, N&B sub_82635A98; KAT,NB (base sub_821B6938)
BANJO_RENUT_HOOK(sub_8222B6E0, GetRenderStateHook<44>);  // pacman-nx: Katamari sub_824DC9F0, N&B sub_82635D10; KAT,NB (base sub_821B6C68)
BANJO_RENUT_HOOK(sub_8222B730, GetRenderStateHook<45>);  // pacman-nx: Katamari sub_824DCA48, N&B sub_82635D68; KAT,NB (base sub_821B6CB8)
BANJO_RENUT_HOOK(sub_8222B690, GetRenderStateHook<46>);  // pacman-nx: Katamari sub_824DC998, N&B sub_82635CB8; KAT,NB (base sub_821B6C18)
BANJO_RENUT_HOOK(sub_8222B780, GetRenderStateHook<47>);  // pacman-nx: Katamari sub_824DCAA0, N&B sub_82635D78; KAT,NB (base sub_821B6D08)
BANJO_RENUT_HOOK(sub_8222B558, GetRenderStateHook<48>);  // pacman-nx: Katamari sub_824DC860, N&B sub_82635BB8; KAT,NB (base sub_821B6AE0)
BANJO_RENUT_HOOK(sub_8222B580, GetRenderStateHook<49>);  // pacman-nx: Katamari sub_824DC888, N&B sub_82635BE0; KAT,NB (base sub_821B6B08)
BANJO_RENUT_HOOK(sub_8222B3C0, GetRenderStateHook<50>);  // pacman-nx: Katamari sub_824DC6C8, N&B sub_82635AB8; KAT,NB (base sub_821B6948)
BANJO_RENUT_HOOK(sub_8222B470, GetRenderStateHook<51>);  // pacman-nx: Katamari sub_824DC778, N&B sub_82635B68; KAT,NB (base sub_821B69F8)
BANJO_RENUT_HOOK(sub_8222B528, GetRenderStateHook<52>);  // pacman-nx: Katamari sub_824DC830, N&B sub_82635B88; KAT,NB (base sub_821B6AB0)
BANJO_RENUT_HOOK(sub_8222B5C0, GetRenderStateHook<53>);  // pacman-nx: Katamari sub_824DC8C8, N&B sub_82635BE8; KAT,NB (base sub_821B6B48)
BANJO_RENUT_HOOK(sub_8222B600, GetRenderStateHook<54>);  // pacman-nx: Katamari sub_824DC908, N&B sub_82635C28; KAT,NB (base sub_821B6B88)
BANJO_RENUT_HOOK(sub_8222B640, GetRenderStateHook<55>);  // pacman-nx: Katamari sub_824DC948, N&B sub_82635C68; KAT,NB (base sub_821B6BC8)
BANJO_RENUT_HOOK(sub_8222B680, GetRenderStateHook<56>);  // pacman-nx: Katamari sub_824DC988, N&B sub_82635CA8; KAT,NB (base sub_821B6C08)
BANJO_RENUT_HOOK(sub_8222BE38, GetRenderStateHook<57>);  // pacman-nx: Katamari sub_824DD1B8, N&B sub_826363F0; KAT,NB (base sub_821B73C0)
BANJO_RENUT_HOOK(sub_8222BDC8, GetRenderStateHook<58>);  // pacman-nx: Katamari sub_824DD148, N&B sub_82636380; KAT,NB (base sub_821B7350)
BANJO_RENUT_HOOK(sub_8222BE00, GetRenderStateHook<59>);  // pacman-nx: Katamari sub_824DD180, N&B sub_826363B8; KAT,NB (base sub_821B7388)
BANJO_RENUT_HOOK(sub_8222B9F0, GetRenderStateHook<60>);  // pacman-nx: Katamari sub_824DCD10, N&B sub_82635FE8; KAT,NB (base sub_821B6F78)
BANJO_RENUT_HOOK(sub_8222BA00, GetRenderStateHook<61>);  // pacman-nx: Katamari sub_824DCD20, N&B sub_82635FF8; KAT,NB (base sub_821B6F88)
BANJO_RENUT_HOOK(sub_8222BA10, GetRenderStateHook<62>);  // pacman-nx: Katamari sub_824DCD30, N&B sub_82636008; KAT,NB (base sub_821B6F98)
BANJO_RENUT_HOOK(sub_8222BA20, GetRenderStateHook<63>);  // pacman-nx: Katamari sub_824DCD40, N&B sub_82636018; KAT,NB (base sub_821B6FA8)
BANJO_RENUT_HOOK(sub_8222BA30, GetRenderStateHook<64>);  // pacman-nx: Katamari sub_824DCD50, N&B sub_82636028; KAT,NB (base sub_821B6FB8)
BANJO_RENUT_HOOK(sub_8222BA40, GetRenderStateHook<65>);  // pacman-nx: Katamari sub_824DCD60, N&B sub_82636038; KAT,NB (base sub_821B6FC8)
BANJO_RENUT_HOOK(sub_8222BA50, GetRenderStateHook<66>);  // pacman-nx: Katamari sub_824DCD70, N&B sub_82636048; KAT,NB (base sub_821B6FD8)
BANJO_RENUT_HOOK(sub_8222BA60, GetRenderStateHook<67>);  // pacman-nx: Katamari sub_824DCD80, N&B sub_82636058; KAT,NB (base sub_821B6FE8)
BANJO_RENUT_HOOK(sub_8222BA70, GetRenderStateHook<68>);  // pacman-nx: Katamari sub_824DCD90, N&B sub_82636068; KAT,NB (base sub_821B6FF8)
BANJO_RENUT_HOOK(sub_8222BA80, GetRenderStateHook<69>);  // pacman-nx: Katamari sub_824DCDA0, N&B sub_82636078; KAT,NB (base sub_821B7008)
BANJO_RENUT_HOOK(sub_8222BA90, GetRenderStateHook<70>);  // pacman-nx: Katamari sub_824DCDB0, N&B sub_82636088; KAT,NB (base sub_821B7018)
BANJO_RENUT_HOOK(sub_8222BAA0, GetRenderStateHook<71>);  // pacman-nx: Katamari sub_824DCDC0, N&B sub_82636098; KAT,NB (base sub_821B7028)
BANJO_RENUT_HOOK(sub_8222BAB0, GetRenderStateHook<72>);  // pacman-nx: Katamari sub_824DCDD0, N&B sub_826360A8; KAT,NB (base sub_821B7038)
BANJO_RENUT_HOOK(sub_8222BAC0, GetRenderStateHook<73>);  // pacman-nx: Katamari sub_824DCDE0, N&B sub_826360B8; KAT,NB (base sub_821B7048)
BANJO_RENUT_HOOK(sub_8222BAD0, GetRenderStateHook<74>);  // pacman-nx: Katamari sub_824DCDF0, N&B sub_826360C8; KAT,NB (base sub_821B7058)
BANJO_RENUT_HOOK(sub_8222BAE0, GetRenderStateHook<75>);  // pacman-nx: Katamari sub_824DCE00, N&B sub_826360D8; KAT,NB (base sub_821B7068)
BANJO_RENUT_HOOK(sub_8222BB30, GetRenderStateHook<76>);  // pacman-nx: Katamari sub_824DCE50, N&B sub_826360E8; KAT,NB (base sub_821B70B8)
BANJO_RENUT_HOOK(sub_8222BBD0, GetRenderStateHook<77>);  // pacman-nx: Katamari sub_824DCF08, N&B sub_82636188; KAT,NB (base sub_821B7158)
BANJO_RENUT_HOOK(sub_8222BC68, GetRenderStateHook<78>);  // pacman-nx: Katamari sub_824DCFB8, N&B sub_82636220; KAT,NB (base sub_821B71F0)
BANJO_RENUT_HOOK(sub_8222BD00, GetRenderStateHook<79>);  // pacman-nx: Katamari sub_824DD068, N&B sub_826362B8; KAT,NB (base sub_821B7288)
BANJO_RENUT_HOOK(sub_8222BD98, GetRenderStateHook<80>);  // pacman-nx: Katamari sub_824DD118, N&B sub_82636350; KAT,NB (base sub_821B7320)
BANJO_RENUT_HOOK(sub_8222BE70, GetRenderStateHook<81>);  // pacman-nx: Katamari sub_824DD1F0, N&B sub_82636428; KAT,NB (base sub_821B73F8)
BANJO_RENUT_HOOK(sub_8222BEA0, GetRenderStateHook<82>);  // pacman-nx: Katamari sub_824DD220, N&B sub_82636458; KAT,NB (base sub_821B7428)
BANJO_RENUT_HOOK(sub_8222BED0, GetRenderStateHook<83>);  // pacman-nx: Katamari sub_824DD250, N&B sub_82636488; KAT,NB (base sub_821B7458)
BANJO_RENUT_HOOK(sub_8222BEF8, GetRenderStateHook<84>);  // pacman-nx: Katamari sub_824DD278, N&B sub_826364B0; KAT,NB (base sub_821B7480)
BANJO_RENUT_HOOK(sub_8222BF28, GetRenderStateHook<85>);  // pacman-nx: Katamari sub_824DD2A8, N&B sub_826364E0; KAT,NB (base sub_821B74B0)
BANJO_RENUT_HOOK(sub_8222BF58, GetRenderStateHook<86>);  // pacman-nx: Katamari sub_824DD2E8, N&B sub_82636510; KAT,NB (base sub_821B74E0)
BANJO_RENUT_HOOK(sub_8222BF88, GetRenderStateHook<87>);  // pacman-nx: Katamari sub_824DD318, N&B sub_82636540; KAT,NB (base sub_821B7510)
BANJO_RENUT_HOOK(sub_8222BFB0, GetRenderStateHook<88>);  // pacman-nx: Katamari sub_824DD340, N&B sub_82636568; KAT,NB (base sub_821B7538)
BANJO_RENUT_HOOK(sub_8222BFE0, GetRenderStateHook<89>);  // pacman-nx: Katamari sub_824DD370, N&B sub_82636598; KAT,NB (base sub_821B7568)
BANJO_RENUT_HOOK(sub_8222C0A0, GetRenderStateHook<90>);  // pacman-nx: Katamari sub_824DD430, N&B sub_82636600; KAT,NB (base sub_821B7628)
BANJO_RENUT_HOOK(sub_8222C0D0, GetRenderStateHook<91>);  // pacman-nx: Katamari sub_824DD460, N&B sub_82636630; KAT,NB (base sub_821B7658)
BANJO_RENUT_HOOK(sub_8222C100, GetRenderStateHook<92>);  // pacman-nx: Katamari sub_824DD490, N&B sub_82636660; KAT,NB (base sub_821B7688)
BANJO_RENUT_HOOK(sub_8222C128, GetRenderStateHook<93>);  // pacman-nx: Katamari sub_824DD4B8, N&B sub_82636688; KAT,NB (base sub_821B76B0)
BANJO_RENUT_HOOK(sub_8222C138, GetRenderStateHook<94>);  // pacman-nx: Katamari sub_824DD4C8, N&B sub_82636698; KAT,NB (base sub_821B76C0)
BANJO_RENUT_HOOK(sub_8222C150, GetRenderStateHook<95>);  // pacman-nx: Katamari sub_824DD4E0, N&B sub_826366B0; KAT,NB (base sub_821B76D8)
BANJO_RENUT_HOOK(sub_8222C008, GetRenderStateHook<96>);  // pacman-nx: Katamari sub_824DD398, N&B sub_826365C0; KAT,NB (base sub_821B7590)
BANJO_RENUT_HOOK(sub_8222C070, GetRenderStateHook<97>);  // pacman-nx: Katamari sub_824DD400, N&B sub_826365D0; KAT,NB (base sub_821B75F8)
BANJO_RENUT_HOOK(sub_8222AF38, GetRenderStateHook<98>);  // pacman-nx: Katamari sub_824DC248, N&B sub_82635688; KAT,NB (base sub_821B64C0)
BANJO_RENUT_HOOK(sub_8222AF88, GetRenderStateHook<99>);  // pacman-nx: Katamari sub_824DC298, N&B sub_826356D8; KAT,NB (base sub_821B6510)
BANJO_RENUT_HOOK(sub_8222AFD8, GetRenderStateHook<100>);  // pacman-nx: Katamari sub_824DC2E8, N&B sub_82635730; KAT,NB (base sub_821B6560)

// Sampler state getters (off_82E50BD0, field 0).
BANJO_RENUT_HOOK(sub_8222C910, GetSamplerStateHook<0>);  // pacman-nx: Katamari sub_824DDC68, N&B sub_82636C00; KAT,NB (base sub_821B7E98)
BANJO_RENUT_HOOK(sub_8222C960, GetSamplerStateHook<1>);  // pacman-nx: Katamari sub_824DDCB8, N&B sub_82636C18; KAT,NB (base sub_821B7EE8)
BANJO_RENUT_HOOK(sub_8222C9B0, GetSamplerStateHook<2>);  // pacman-nx: Katamari sub_824DDD08, N&B sub_82636C68; KAT,NB (base sub_821B7F38)
BANJO_RENUT_HOOK(sub_8222C8B0, GetSamplerStateHook<3>);  // pacman-nx: Katamari sub_824DDC10, N&B sub_82636BD8; KAT,NB (base sub_821B7E38)
BANJO_RENUT_HOOK(sub_8222C3D0, GetSamplerStateHook<4>);  // pacman-nx: Katamari sub_824DD740, N&B sub_826367A0; KAT,NB (base sub_821B7958)
BANJO_RENUT_HOOK(sub_8222C228, GetSamplerStateHook<5>);  // pacman-nx: Katamari sub_824DD5B0, N&B sub_826366C0; KAT,NB (base sub_821B77B0)
BANJO_RENUT_HOOK(sub_8222C4E8, GetSamplerStateHook<6>);  // pacman-nx: Katamari sub_824DD850, N&B sub_82636878; KAT,NB (base sub_821B7A70)
BANJO_RENUT_HOOK(sub_8222C728, GetSamplerStateHook<7>);  // pacman-nx: Katamari sub_824DDA80, N&B sub_82636AB8; KAT,NB (base sub_821B7CB0)
BANJO_RENUT_HOOK(sub_8222C7D8, GetSamplerStateHook<8>);  // pacman-nx: Katamari sub_824DDB30, N&B sub_82636B00; KAT,NB (base sub_821B7D60)
BANJO_RENUT_HOOK(sub_8222C610, GetSamplerStateHook<9>);  // pacman-nx: Katamari sub_824DD968, N&B sub_826369A0; KAT,NB (base sub_821B7B98)
BANJO_RENUT_HOOK(sub_8222C498, GetSamplerStateHook<10>);  // pacman-nx: Katamari sub_824DD800, N&B sub_82636868; KAT,NB (base sub_821B7A20)
BANJO_RENUT_HOOK(sub_8222C2F8, GetSamplerStateHook<11>);  // pacman-nx: Katamari sub_824DD670, N&B sub_82636790; KAT,NB (base sub_821B7880)
BANJO_RENUT_HOOK(sub_8222C598, GetSamplerStateHook<12>);  // pacman-nx: Katamari sub_824DD8F0, N&B sub_82636928; KAT,NB (base sub_821B7B20)
BANJO_RENUT_HOOK(sub_8222C858, GetSamplerStateHook<13>);  // pacman-nx: Katamari sub_824DDBB0, N&B sub_82636B80; KAT,NB (base sub_821B7DE0)
BANJO_RENUT_HOOK(sub_8222CA08, GetSamplerStateHook<14>);  // pacman-nx: Katamari sub_824DDD60, N&B sub_82636CC0; KAT,NB (base sub_821B7F90)
BANJO_RENUT_HOOK(sub_8222C680, GetSamplerStateHook<15>);  // pacman-nx: Katamari sub_824DD9D8, N&B sub_82636A10; KAT,NB (base sub_821B7C08)
BANJO_RENUT_HOOK(sub_8222CA60, GetSamplerStateHook<16>);  // pacman-nx: Katamari sub_824DDDB8, N&B sub_82636D18; KAT,NB (base sub_821B7FE8)
BANJO_RENUT_HOOK(sub_8222CAB8, GetSamplerStateHook<17>);  // pacman-nx: Katamari sub_824DDE10, N&B sub_82636D70; KAT,NB (base sub_821B8040)
BANJO_RENUT_HOOK(sub_8222CB10, GetSamplerStateHook<18>);  // pacman-nx: Katamari sub_824DDE68, N&B sub_82636DC8; KAT,NB (base sub_821B8098)
BANJO_RENUT_HOOK(sub_8222CB70, GetSamplerStateHook<19>);  // pacman-nx: Katamari sub_824DDEC8, N&B sub_82636E28; KAT,NB (base sub_821B80F8)
