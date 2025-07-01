// Test script to verify tier system works with all donation tiers
const testTiers = [
  'bronze',
  'silver', 
  'gold',
  'platinum',
  'emerald',
  'topaz',
  'ruby',
  'sapphire'
];

// Mock the getTierDisplay function from ProductCard
function getTierDisplay(tierName) {
  const tier = tierName.toLowerCase();
  
  // Premium tiers (Sapphire, Ruby, Topaz, Emerald, Platinum)
  if (tier.includes('sapphire')) {
    return { icon: 'FaCrown', color: 'text-blue-600', bgColor: 'bg-blue-100' };
  } else if (tier.includes('ruby')) {
    return { icon: 'FaCrown', color: 'text-red-600', bgColor: 'bg-red-100' };
  } else if (tier.includes('topaz')) {
    return { icon: 'FaCrown', color: 'text-yellow-500', bgColor: 'bg-yellow-100' };
  } else if (tier.includes('emerald')) {
    return { icon: 'FaCrown', color: 'text-green-600', bgColor: 'bg-green-100' };
  } else if (tier.includes('platinum')) {
    return { icon: 'FaCrown', color: 'text-gray-700', bgColor: 'bg-gray-200' };
  } 
  // Standard tiers (Gold, Silver, Bronze)
  else if (tier.includes('gold')) {
    return { icon: 'FaStar', color: 'text-yellow-600', bgColor: 'bg-yellow-100' };
  } else if (tier.includes('silver')) {
    return { icon: 'FaStar', color: 'text-gray-600', bgColor: 'bg-gray-100' };
  } else if (tier.includes('bronze')) {
    return { icon: 'FaGem', color: 'text-orange-600', bgColor: 'bg-orange-100' };
  } 
  // Fallback for unknown tiers
  else {
    return { icon: 'FaHeart', color: 'text-pink-600', bgColor: 'bg-pink-100' };
  }
}

console.log('Testing tier system with all donation tiers:\n');

testTiers.forEach(tier => {
  const display = getTierDisplay(tier);
  console.log(`${tier.toUpperCase()}:`);
  console.log(`  Icon: ${display.icon}`);
  console.log(`  Color: ${display.color}`);
  console.log(`  Background: ${display.bgColor}`);
  console.log('');
});

// Test edge cases
console.log('Testing edge cases:');
const edgeCases = ['unknown', 'DIAMOND', 'SAPPHIRE', 'ruby', 'EMERALD'];
edgeCases.forEach(tier => {
  const display = getTierDisplay(tier);
  console.log(`${tier}: ${display.icon} with ${display.color} on ${display.bgColor}`);
});

console.log('\n✅ Tier system test completed!'); 