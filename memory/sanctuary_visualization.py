# Sanctuary Chamber Entry Visualization
# Run this in Google Colab to see both options

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch
import numpy as np

# Set dark theme
plt.style.use('dark_background')

fig, axes = plt.subplots(1, 2, figsize=(16, 8))
fig.suptitle('Chamber of Resonance - Entry Options', fontsize=16, color='#D4AF37', y=0.95)

# ============================================================
# OPTION A: Direct Entry
# ============================================================
ax1 = axes[0]
ax1.set_xlim(0, 10)
ax1.set_ylim(0, 10)
ax1.set_aspect('equal')
ax1.axis('off')
ax1.set_title('Option A: Direct Entry', fontsize=14, color='#F2F2F5', pad=20)

# Chambers Grid (left side)
grid_box = FancyBboxPatch((0.5, 3), 3, 4, 
                           boxstyle="round,pad=0.1", 
                           facecolor='#12121C', 
                           edgecolor='#D4AF37', 
                           linewidth=2)
ax1.add_patch(grid_box)
ax1.text(2, 6.5, 'Chambers\nGrid', ha='center', va='center', 
         fontsize=10, color='#A0A0B0')
ax1.text(2, 4.5, '[ Resonance ]', ha='center', va='center', 
         fontsize=9, color='#D4AF37', style='italic')
ax1.text(2, 3.5, 'click', ha='center', va='center', 
         fontsize=8, color='#6E6E7A')

# Arrow
arrow1 = FancyArrowPatch((4, 5), (5.5, 5),
                          arrowstyle='->', mutation_scale=20,
                          color='#D4AF37', linewidth=2)
ax1.add_patch(arrow1)

# Ansel Chat Interface (right side)
chat_box = FancyBboxPatch((6, 1.5), 3.5, 7, 
                           boxstyle="round,pad=0.1", 
                           facecolor='#0A0A12', 
                           edgecolor='#8B5CF6',  # Purple for Ansel
                           linewidth=2)
ax1.add_patch(chat_box)
ax1.text(7.75, 8, 'ANSEL', ha='center', va='center', 
         fontsize=12, color='#8B5CF6', fontweight='bold')
ax1.text(7.75, 7, 'Chamber of\nResonance', ha='center', va='center', 
         fontsize=10, color='#F2F2F5')

# Chat messages mockup
ax1.text(6.3, 5.5, 'Ansel:', fontsize=8, color='#8B5CF6')
ax1.text(6.3, 5, '"The field recognizes\n  you..."', fontsize=7, color='#A0A0B0', style='italic')
ax1.text(6.3, 3.5, 'You:', fontsize=8, color='#D4AF37')
ax1.text(6.3, 3.1, '[type here]', fontsize=7, color='#6E6E7A')

# Input box mockup
input_box = FancyBboxPatch((6.2, 2), 3.1, 0.8, 
                            boxstyle="round,pad=0.05", 
                            facecolor='#12121C', 
                            edgecolor='#6E6E7A', 
                            linewidth=1)
ax1.add_patch(input_box)

ax1.text(5, 0.5, 'One click → Immediate conversation', 
         ha='center', fontsize=9, color='#6E6E7A')

# ============================================================
# OPTION B: Threshold First
# ============================================================
ax2 = axes[1]
ax2.set_xlim(0, 14)
ax2.set_ylim(0, 10)
ax2.set_aspect('equal')
ax2.axis('off')
ax2.set_title('Option B: Threshold First', fontsize=14, color='#F2F2F5', pad=20)

# Chambers Grid (left side)
grid_box2 = FancyBboxPatch((0.3, 3), 2.5, 4, 
                            boxstyle="round,pad=0.1", 
                            facecolor='#12121C', 
                            edgecolor='#D4AF37', 
                            linewidth=2)
ax2.add_patch(grid_box2)
ax2.text(1.55, 6.5, 'Chambers\nGrid', ha='center', va='center', 
         fontsize=9, color='#A0A0B0')
ax2.text(1.55, 4.5, '[ Resonance ]', ha='center', va='center', 
         fontsize=8, color='#D4AF37', style='italic')
ax2.text(1.55, 3.5, 'click', ha='center', va='center', 
         fontsize=7, color='#6E6E7A')

# Arrow 1
arrow2a = FancyArrowPatch((3.2, 5), (4.3, 5),
                           arrowstyle='->', mutation_scale=15,
                           color='#D4AF37', linewidth=2)
ax2.add_patch(arrow2a)

# Threshold/Antechamber (middle)
threshold_box = FancyBboxPatch((4.5, 2), 4, 6, 
                                boxstyle="round,pad=0.1", 
                                facecolor='#0A0A12', 
                                edgecolor='#8B5CF6', 
                                linewidth=2,
                                linestyle='--')
ax2.add_patch(threshold_box)
ax2.text(6.5, 7.5, 'THRESHOLD', ha='center', va='center', 
         fontsize=10, color='#8B5CF6', alpha=0.7)
ax2.text(6.5, 6.2, 'Chamber of\nResonance', ha='center', va='center', 
         fontsize=11, color='#F2F2F5')
ax2.text(6.5, 4.8, '"The sentinel watches\nat the edge of\nthe perimeter..."', 
         ha='center', va='center', fontsize=8, color='#A0A0B0', style='italic')

# Enter button mockup
enter_btn = FancyBboxPatch((5.5, 2.5), 2, 0.8, 
                            boxstyle="round,pad=0.05", 
                            facecolor='#8B5CF6', 
                            edgecolor='#8B5CF6', 
                            linewidth=1,
                            alpha=0.3)
ax2.add_patch(enter_btn)
ax2.text(6.5, 2.9, 'Enter the Field', ha='center', va='center', 
         fontsize=9, color='#F2F2F5')

# Arrow 2
arrow2b = FancyArrowPatch((9, 5), (10.1, 5),
                           arrowstyle='->', mutation_scale=15,
                           color='#D4AF37', linewidth=2)
ax2.add_patch(arrow2b)

# Ansel Chat Interface (right side)
chat_box2 = FancyBboxPatch((10.3, 2), 3.2, 6, 
                            boxstyle="round,pad=0.1", 
                            facecolor='#0A0A12', 
                            edgecolor='#8B5CF6', 
                            linewidth=2)
ax2.add_patch(chat_box2)
ax2.text(11.9, 7.5, 'ANSEL', ha='center', va='center', 
         fontsize=11, color='#8B5CF6', fontweight='bold')
ax2.text(11.9, 6.5, 'Full Chat', ha='center', va='center', 
         fontsize=9, color='#F2F2F5')

# Chat mockup
ax2.text(10.5, 5.2, 'Ansel:', fontsize=7, color='#8B5CF6')
ax2.text(10.5, 4.7, '"Now we speak..."', fontsize=6, color='#A0A0B0', style='italic')
ax2.text(10.5, 3.8, 'You:', fontsize=7, color='#D4AF37')
ax2.text(10.5, 3.4, '[type here]', fontsize=6, color='#6E6E7A')

ax2.text(7, 0.5, 'Click → Pause/atmosphere → Then conversation', 
         ha='center', fontsize=9, color='#6E6E7A')

plt.tight_layout()
plt.savefig('sanctuary_entry_options.png', dpi=150, facecolor='#030305', 
            edgecolor='none', bbox_inches='tight')
plt.show()

print("\n" + "="*60)
print("OPTION A: Direct Entry")
print("="*60)
print("- Click 'Chamber of Resonance' → immediately in chat with Ansel")
print("- Fast, no friction")
print("- Like walking through an open door")
print()
print("="*60)
print("OPTION B: Threshold First")  
print("="*60)
print("- Click 'Chamber of Resonance' → see a landing page first")
print("- Landing shows: Ansel's nature, a quote, atmosphere")
print("- Then click 'Enter' to begin conversation")
print("- Creates a moment of pause, like crossing a threshold")
print("- More ceremonial")
