import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from scipy.stats import pearsonr
import warnings
import os
warnings.filterwarnings('ignore')

# Create outputs directory if it doesn't exist
os.makedirs('outputs', exist_ok=True)

# ─── LOAD & PREP ─────────────────────────────────────────────────────────────
df = pd.read_csv('E:\\football\\session-run-2-2026-03-18.csv')
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
df = df.sort_values('Timestamp').reset_index(drop=True)

# Create elapsed time (0–4.1 min, matching sample plots)
df['elapsed_min'] = np.linspace(0, 4.1, len(df))

# Clean speed outliers (sensor spikes)
df['Speed_clean'] = df['Speed (km/h)'].clip(0, 35)
df['HR_clean']    = df['Heart Rate (BPM)'].clip(90, 210)
df['Accel_clean'] = df['Acceleration (m/s²)'].clip(0, 20)

# GPS — keep only valid coordinates
geo = df[(df['Latitude'] != 0) & (df['Longitude'] != 0)].copy()

# Convert lat/lon → metres (approx)
lat0 = geo['Latitude'].mean()
lon0 = geo['Longitude'].mean()
geo['x_m'] =  (geo['Longitude'] - lon0) * np.cos(np.radians(lat0)) * 111320
geo['y_m'] =  (geo['Latitude']  - lat0) * 111320

# Speed-zone colour map
zone_order  = ['Walking', 'Jogging', 'Running', 'High-speed Running', 'Sprinting']
zone_colors = {'Walking': '#00BFFF', 'Jogging': '#00CC44',
               'Running': '#FFAA00', 'High-speed Running': '#FF4400',
               'Sprinting': '#FF0066'}

# ─── STYLE ───────────────────────────────────────────────────────────────────
DARK_BG = '#0d0d1a'
PANEL_BG = '#111125'
TEXT_COL = '#e0e0e0'
GRID_COL = '#2a2a4a'

def dark_fig(figsize=(14, 6)):
    fig = plt.figure(figsize=figsize, facecolor=DARK_BG)
    return fig

def style_ax(ax, xlabel='', ylabel='', title=''):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors=TEXT_COL, labelsize=8)
    ax.xaxis.label.set_color(TEXT_COL)
    ax.yaxis.label.set_color(TEXT_COL)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
    ax.grid(True, color=GRID_COL, linewidth=0.5, alpha=0.6)
    if xlabel: ax.set_xlabel(xlabel, color=TEXT_COL, fontsize=9)
    if ylabel: ax.set_ylabel(ylabel, color=TEXT_COL, fontsize=9)
    if title:  ax.set_title(title, color=TEXT_COL, fontsize=10, pad=6)

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 1 — GPS Positional Data: Pitch Coverage + Heatmap
# ══════════════════════════════════════════════════════════════════════════════
fig1 = dark_fig(figsize=(16, 5))
fig1.suptitle('GPS Positional Data — Pitch Coverage', color=TEXT_COL, fontsize=13, y=1.01)

gs = gridspec.GridSpec(1, 2, figure=fig1, wspace=0.12)
ax_track = fig1.add_subplot(gs[0])
ax_heat  = fig1.add_subplot(gs[1])

# — Track coloured by speed zone —
for zone in zone_order:
    zdf = geo[geo['Speed Zone'] == zone]
    ax_track.scatter(zdf['x_m'], zdf['y_m'], s=0.6,
                     color=zone_colors[zone], label=zone, alpha=0.7, linewidths=0)

style_ax(ax_track, xlabel='x (m)', ylabel='y (m)', title='Track coloured by Speed Zone')
patches = [mpatches.Patch(color=zone_colors[z], label=z) for z in zone_order]
ax_track.legend(handles=patches, fontsize=7, loc='upper left',
                facecolor='#1a1a2e', edgecolor=GRID_COL, labelcolor=TEXT_COL,
                markerscale=2)

# Start / End markers
ax_track.scatter(geo['x_m'].iloc[0],  geo['y_m'].iloc[0],
                 marker='^', color='#00FF88', s=80, zorder=10, label='Start')
ax_track.scatter(geo['x_m'].iloc[-1], geo['y_m'].iloc[-1],
                 marker='s', color='#FF4444', s=80, zorder=10, label='End')

# — Heatmap —
h, xedg, yedg, img = ax_heat.hist2d(
    geo['x_m'], geo['y_m'], bins=80,
    cmap=LinearSegmentedColormap.from_list('heat', ['#000022','#0000ff','#00ffff','#ffff00','#ff0000']))
cb = fig1.colorbar(img, ax=ax_heat, pad=0.02)
cb.ax.tick_params(colors=TEXT_COL, labelsize=7)
cb.set_label('Sample count', color=TEXT_COL, fontsize=8)

start_leg = [Line2D([0],[0], marker='^', color='w', markerfacecolor='#00FF88', markersize=8, label='Start'),
             Line2D([0],[0], marker='s', color='w', markerfacecolor='#FF4444', markersize=8, label='End')]
ax_heat.scatter(geo['x_m'].iloc[0],  geo['y_m'].iloc[0],  marker='^', color='#00FF88', s=80, zorder=10)
ax_heat.scatter(geo['x_m'].iloc[-1], geo['y_m'].iloc[-1], marker='s', color='#FF4444', s=80, zorder=10)
ax_heat.legend(handles=start_leg, fontsize=7, loc='upper left',
               facecolor='#1a1a2e', edgecolor=GRID_COL, labelcolor=TEXT_COL)
style_ax(ax_heat, xlabel='x (m)', ylabel='y (m)', title='Position Heatmap')

plt.tight_layout()
fig1.savefig('outputs/plot1_gps.png', dpi=150, bbox_inches='tight',
             facecolor=DARK_BG)
plt.close(fig1)
print("Plot 1 saved")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 2 — Speed & Heart Rate Profile
# ══════════════════════════════════════════════════════════════════════════════
# Speed zone thresholds (km/h)
zone_thresh = {'Walking': (0, 6), 'Jogging': (6, 11), 'Running': (11, 18),
               'High-speed Running': (18, 25), 'Sprinting': (25, 40)}
zone_bg_colors = {'Walking': '#1a4a6e', 'Jogging': '#1a5a2a',
                  'Running': '#6e4a00', 'High-speed Running': '#8a2a00',
                  'Sprinting': '#5a0022'}

t = df['elapsed_min'].values
spd = df['Speed_clean'].values
hr  = df['HR_clean'].values

fig2, (ax_s, ax_h) = plt.subplots(2, 1, figsize=(16, 7), facecolor=DARK_BG,
                                   gridspec_kw={'height_ratios': [1.2, 1], 'hspace': 0.06})
fig2.suptitle('Speed & Heart Rate Profile', color=TEXT_COL, fontsize=13, y=1.01)

# — Speed panel —
# Background bands for speed zones
for zone, (lo, hi) in zone_thresh.items():
    ax_s.axhspan(lo, hi, color=zone_bg_colors[zone], alpha=0.35)

ax_s.plot(t, spd, color='white', linewidth=0.6, alpha=0.9)

# Walking / Jogging / Running legend patches
band_patches = [mpatches.Patch(color='#1a4a6e', alpha=0.8, label='Walking'),
                mpatches.Patch(color='#1a5a2a', alpha=0.8, label='Jogging'),
                mpatches.Patch(color='#6e4a00', alpha=0.8, label='Running')]
ax_s.legend(handles=band_patches, fontsize=8, loc='upper right',
            facecolor='#1a1a2e', edgecolor=GRID_COL, labelcolor=TEXT_COL)
ax_s.set_ylim(0, 36)
ax_s.axhline(10, color='white', linewidth=0.6, linestyle='--', alpha=0.4)
style_ax(ax_s, ylabel='Speed (km/h)')
ax_s.set_xticklabels([])

# — HR panel —
hr_cmap = plt.cm.plasma
hr_norm = plt.Normalize(90, 200)

# Colour HR line by intensity
for i in range(len(t)-1):
    ax_h.plot(t[i:i+2], hr[i:i+2], color=hr_cmap(hr_norm(hr[i])), linewidth=1.0)

avg_hr = hr.mean()
ax_h.axhline(avg_hr, color='#FFDD44', linewidth=1.0, linestyle='--', alpha=0.7)
ax_h.text(t[-1]*0.01, avg_hr+2, f'Avg {avg_hr:.0f} bpm', color='#FFDD44', fontsize=8)

# HR zone bands
ax_h.axhspan(90,  120, color='#111144', alpha=0.4)
ax_h.axhspan(120, 150, color='#112244', alpha=0.4)
ax_h.axhspan(150, 180, color='#221100', alpha=0.4)
ax_h.axhspan(180, 210, color='#330000', alpha=0.5)

hr_line = Line2D([0],[0], color='#FF6666', linewidth=1.5, label='HR')
avg_line = Line2D([0],[0], color='#FFDD44', linewidth=1.0, linestyle='--', label=f'Avg {avg_hr:.0f} bpm')
ax_h.legend(handles=[hr_line, avg_line], fontsize=8, loc='upper right',
            facecolor='#1a1a2e', edgecolor=GRID_COL, labelcolor=TEXT_COL)
ax_h.set_ylim(90, 210)
style_ax(ax_h, xlabel='Elapsed Time (min)', ylabel='Heart Rate (BPM)')

plt.tight_layout()
fig2.savefig('outputs/plot2_speed_hr.png', dpi=150, bbox_inches='tight',
             facecolor=DARK_BG)
plt.close(fig2)
print("Plot 2 saved")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 3 — Acceleration Profile & PlayerLoad
# ══════════════════════════════════════════════════════════════════════════════
accel  = df['Accel_clean'].values
pl_cum = df['PlayerLoad (cumulative)'].values
pl_ins = df['PlayerLoad (instant)'].values.clip(0, 0.07)

# Rolling PlayerLoad (5-s window ≈ 5s × 12.9 samples/s ≈ 65 samples)
win = max(1, int(5 * len(df)/246))   # ~65 samples
pl_roll = pd.Series(pl_ins).rolling(win, min_periods=1).mean().values

fig3 = dark_fig(figsize=(14, 9))
fig3.suptitle('Acceleration Profile & PlayerLoad', color=TEXT_COL, fontsize=13)
gs3 = gridspec.GridSpec(2, 2, figure=fig3, hspace=0.38, wspace=0.32)

ax_ai  = fig3.add_subplot(gs3[0, 0])   # instantaneous accel
ax_ad  = fig3.add_subplot(gs3[0, 1])   # accel distribution
ax_plc = fig3.add_subplot(gs3[1, 0])   # cumulative PL
ax_plr = fig3.add_subplot(gs3[1, 1])   # rolling PL intensity

# instantaneous acceleration
ax_ai.fill_between(t, accel, color='#FFAA00', alpha=0.85, linewidth=0)
mean_a = accel.mean()
ax_ai.axhline(mean_a, color='white', linestyle='--', linewidth=0.8, alpha=0.6)
ax_ai.text(t[-1]*0.97, mean_a+0.2, f'Mean {mean_a:.1f} m/s²',
           color='white', fontsize=7, ha='right')
style_ax(ax_ai, xlabel='Time (min)', ylabel='Acceleration (m/s²)',
         title='Instantaneous Acceleration over Time')
ax_ai.set_ylim(0)

# acceleration distribution
ax_ad.hist(accel, bins=60, color='#FFAA00', edgecolor='none', alpha=0.9)
ax_ad.axvline(mean_a, color='white', linestyle='--', linewidth=0.9)
ax_ad.text(mean_a+0.1, ax_ad.get_ylim()[1]*0.85, '--- Mean',
           color='white', fontsize=7)
style_ax(ax_ad, xlabel='Acceleration (m/s²)', ylabel='Frequency',
         title='Acceleration Distribution')

# cumulative PlayerLoad
ax_plc.fill_between(t, pl_cum, color='#00CCCC', alpha=0.7, linewidth=0)
style_ax(ax_plc, xlabel='Time (min)', ylabel='PlayerLoad (AU)',
         title='Cumulative PlayerLoad')
ax_plc.set_ylim(0)

# rolling PlayerLoad intensity
ax_plr.plot(t, pl_roll, color='#44DDAA', linewidth=0.9)
ax_plr.fill_between(t, pl_roll, color='#44DDAA', alpha=0.3)
style_ax(ax_plr, xlabel='Time (min)', ylabel='PlayerLoad (AU)',
         title=f'Rolling PlayerLoad Intensity ({win}-s window)')

plt.tight_layout()
fig3.savefig('outputs/plot3_accel_playerload.png', dpi=150,
             bbox_inches='tight', facecolor=DARK_BG)
plt.close(fig3)
print("Plot 3 saved")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 4 — Body Rotation, Sprint Events & Cumulative Counts
# ══════════════════════════════════════════════════════════════════════════════
rot  = df['Body Rotation (°/s)'].clip(0, 85).values
accel_ev = df['Accel Events'].values
decel_ev = df['Decel Events'].values
sprint_c = df['Sprint Count'].values

# 10-s rolling average of body rotation
win10 = max(1, int(10 * len(df)/246))
rot_roll = pd.Series(rot).rolling(win10, min_periods=1).mean().values

fig4 = dark_fig(figsize=(14, 9))
fig4.suptitle('Body Rotation, Sprint Events & Cumulative Counts', color=TEXT_COL, fontsize=13)
gs4 = gridspec.GridSpec(2, 2, figure=fig4, hspace=0.38, wspace=0.32)

ax_rt  = fig4.add_subplot(gs4[0, 0])   # rotation over time
ax_rd  = fig4.add_subplot(gs4[0, 1])   # rotation distribution
ax_ev  = fig4.add_subplot(gs4[1, 0])   # cumulative events
ax_sv  = fig4.add_subplot(gs4[1, 1])   # speed vs rotation scatter

# rotation over time
ax_rt.fill_between(t, rot, color='#BB66FF', alpha=0.45, linewidth=0)
ax_rt.plot(t, rot_roll, color='#FF88FF', linewidth=0.9, label='10-s rolling avg')
ax_rt.legend(fontsize=7, loc='upper right', facecolor='#1a1a2e',
             edgecolor=GRID_COL, labelcolor=TEXT_COL)
style_ax(ax_rt, xlabel='Time (min)', ylabel='Angular velocity (°/s)',
         title='Body Rotation Over Time')

# rotation distribution
mean_r = rot.mean()
ax_rd.hist(rot, bins=60, color='#CC66FF', edgecolor='none', alpha=0.9)
ax_rd.axvline(mean_r, color='white', linestyle='--', linewidth=0.9)
ax_rd.text(mean_r+0.5, ax_rd.get_ylim()[1]*0.85, f'--- Mean {mean_r:.1f} °/s',
           color='white', fontsize=7)
style_ax(ax_rd, xlabel='Body Rotation (°/s)', ylabel='Frequency',
         title='Body Rotation Distribution')

# cumulative events
ax_ev.plot(t, accel_ev, color='#FFAA00', linewidth=1.0, label='Accel Events')
ax_ev.plot(t, decel_ev, color='#FF4466', linewidth=1.0, label='Decel Events')
ax_ev.plot(t, sprint_c, color='#44FFAA', linewidth=1.0, label='Sprint Count')
ax_ev.legend(fontsize=7, loc='upper left', facecolor='#1a1a2e',
             edgecolor=GRID_COL, labelcolor=TEXT_COL)
style_ax(ax_ev, xlabel='Time (min)', ylabel='Cumulative Count',
         title='Cumulative Events Over Time')

# speed vs body rotation scatter — coloured by PlayerLoad instant
sc = ax_sv.scatter(spd, rot, c=pl_ins, cmap='plasma', s=0.8, alpha=0.6, linewidths=0)
cb4 = fig4.colorbar(sc, ax=ax_sv, pad=0.02)
cb4.ax.tick_params(colors=TEXT_COL, labelsize=7)
cb4.set_label('PlayerLoad (inst)', color=TEXT_COL, fontsize=8)
style_ax(ax_sv, xlabel='Speed (km/h)', ylabel='Body Rotation (°/s)',
         title='Speed vs Body Rotation')

plt.tight_layout()
fig4.savefig('outputs/plot4_rotation_events.png', dpi=150,
             bbox_inches='tight', facecolor=DARK_BG)
plt.close(fig4)
print("Plot 4 saved")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 5 — Additional: Correlation Matrix
# ══════════════════════════════════════════════════════════════════════════════
import seaborn as sns

corr_cols = ['Speed_clean', 'HR_clean', 'Accel_clean',
             'PlayerLoad (instant)', 'Body Rotation (°/s)', 'SpO2 (%)']
corr_labels = ['Speed', 'Heart Rate', 'Acceleration',
               'PlayerLoad (inst)', 'Body Rotation', 'SpO2']

corr_df = df[corr_cols].copy()
corr_df.columns = corr_labels
corr_matrix = corr_df.corr()

fig5, ax5 = plt.subplots(figsize=(9, 7), facecolor=DARK_BG)
mask = np.zeros_like(corr_matrix, dtype=bool)
np.fill_diagonal(mask, False)

cmap_corr = sns.diverging_palette(220, 10, as_cmap=True)
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap=cmap_corr,
            center=0, vmin=-1, vmax=1, ax=ax5,
            annot_kws={'size': 11, 'color': 'white'},
            linewidths=0.5, linecolor=DARK_BG,
            cbar_kws={'shrink': 0.8})

ax5.set_facecolor(DARK_BG)
ax5.tick_params(colors=TEXT_COL, labelsize=10)
ax5.set_title('Metric Correlation Matrix', color=TEXT_COL, fontsize=13, pad=12)
cb5 = ax5.collections[0].colorbar
cb5.ax.tick_params(colors=TEXT_COL)
cb5.set_label('Pearson r', color=TEXT_COL, fontsize=9)

plt.tight_layout()
fig5.savefig('outputs/plot5_correlation.png', dpi=150,
             bbox_inches='tight', facecolor=DARK_BG)
plt.close(fig5)
print("Plot 5 saved")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 6 — Additional: Speed Zone Distribution + HR Zone Distribution
# ══════════════════════════════════════════════════════════════════════════════
fig6, (ax6a, ax6b) = plt.subplots(1, 2, figsize=(14, 5), facecolor=DARK_BG)
fig6.suptitle('Time Distribution by Zone', color=TEXT_COL, fontsize=13)

# Speed zone %
zone_pct = df['Speed Zone'].value_counts(normalize=True).reindex(zone_order) * 100
bars_s = ax6a.barh(zone_pct.index, zone_pct.values,
                   color=[zone_colors[z] for z in zone_pct.index], edgecolor='none')
for bar, val in zip(bars_s, zone_pct.values):
    ax6a.text(val + 0.4, bar.get_y() + bar.get_height()/2,
              f'{val:.1f}%', va='center', color=TEXT_COL, fontsize=9)
style_ax(ax6a, xlabel='% of Session', title='Speed Zone Distribution')

# HR zone %
hr_bins = [90, 120, 140, 160, 180, 210]
hr_zone_labels = ['Zone 1\n(90–120)', 'Zone 2\n(120–140)', 'Zone 3\n(140–160)',
                  'Zone 4\n(160–180)', 'Zone 5\n(180+)']
hr_zone_colors = ['#1a6eaa', '#1a9a44', '#aaaa00', '#cc5500', '#cc0000']
hr_zone_counts = pd.cut(hr, bins=hr_bins, labels=hr_zone_labels).value_counts().reindex(hr_zone_labels)
hr_zone_pct = hr_zone_counts / hr_zone_counts.sum() * 100

bars_h = ax6b.barh(hr_zone_pct.index, hr_zone_pct.values,
                   color=hr_zone_colors, edgecolor='none')
for bar, val in zip(bars_h, hr_zone_pct.values):
    ax6b.text(val + 0.4, bar.get_y() + bar.get_height()/2,
              f'{val:.1f}%', va='center', color=TEXT_COL, fontsize=9)
style_ax(ax6b, xlabel='% of Session', title='Heart Rate Zone Distribution')

plt.tight_layout()
fig6.savefig('outputs/plot6_zone_distribution.png', dpi=150,
             bbox_inches='tight', facecolor=DARK_BG)
plt.close(fig6)
print("Plot 6 saved")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 7 — Additional: Fatigue Indicators (rolling max speed + HR)
# ══════════════════════════════════════════════════════════════════════════════
win_fat = max(1, len(df)//20)   # ~5% of session per window
rolling_max_spd = pd.Series(spd).rolling(win_fat).max().values
rolling_avg_hr  = pd.Series(hr).rolling(win_fat).mean().values
rolling_avg_pl  = pd.Series(pl_ins).rolling(win_fat).mean().values

fig7, axes7 = plt.subplots(3, 1, figsize=(14, 8), facecolor=DARK_BG,
                            sharex=True, gridspec_kw={'hspace': 0.12})
fig7.suptitle('Fatigue Indicators Across Session', color=TEXT_COL, fontsize=13)

axes7[0].fill_between(t, rolling_max_spd, color='#00AAFF', alpha=0.7)
axes7[0].plot(t, rolling_max_spd, color='#88DDFF', linewidth=0.8)
style_ax(axes7[0], ylabel='Peak Speed (km/h)', title='Rolling Peak Speed')

axes7[1].fill_between(t, rolling_avg_hr, color='#FF6666', alpha=0.6)
axes7[1].plot(t, rolling_avg_hr, color='#FF9999', linewidth=0.8)
style_ax(axes7[1], ylabel='Avg HR (BPM)', title='Rolling Average Heart Rate')

axes7[2].fill_between(t, rolling_avg_pl, color='#FFAA44', alpha=0.6)
axes7[2].plot(t, rolling_avg_pl, color='#FFCC88', linewidth=0.8)
style_ax(axes7[2], xlabel='Elapsed Time (min)',
         ylabel='PlayerLoad (AU)', title='Rolling Avg PlayerLoad Intensity')

plt.tight_layout()
fig7.savefig('outputs/plot7_fatigue.png', dpi=150,
             bbox_inches='tight', facecolor=DARK_BG)
plt.close(fig7)
print("Plot 7 saved")

print("\nAll plots saved to outputs/")
