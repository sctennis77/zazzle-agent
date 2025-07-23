/**
 * Downloads an image from a URL with a given filename
 */
export const downloadImage = async (imageUrl: string, filename: string): Promise<void> => {
  try {
    // Fetch the image
    const response = await fetch(imageUrl, {
      mode: 'cors',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.statusText}`);
    }
    
    // Get the blob
    const blob = await response.blob();
    
    // Create object URL
    const objectUrl = URL.createObjectURL(blob);
    
    // Create temporary link element
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = filename;
    
    // Append to body, click, and remove
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up object URL
    URL.revokeObjectURL(objectUrl);
    
  } catch (error) {
    console.error('Error downloading image:', error);
    
    // Fallback: try opening in new tab
    try {
      const link = document.createElement('a');
      link.href = imageUrl;
      link.target = '_blank';
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (fallbackError) {
      console.error('Fallback download failed:', fallbackError);
      throw new Error('Unable to download image');
    }
  }
};

/**
 * Generates a clean filename from image title and post ID
 */
export const generateImageFilename = (imageTitle: string, postId: string): string => {
  // Clean the title: remove special characters, replace spaces with hyphens
  const cleanTitle = imageTitle
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .substring(0, 50); // Limit length
  
  const cleanPostId = postId.replace(/[^a-z0-9]/gi, '');
  
  return `clouvel-${cleanTitle}-${cleanPostId}.jpg`;
};