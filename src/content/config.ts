import { defineCollection, z } from 'astro:content';

const books = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    language: z.enum(['English', 'Hindi', 'Bengali', 'Russian', 'Marathi', 'Odia']),
    publisher: z.string().optional(),
    price: z.number().optional(),
    currency: z.string().default('INR'),
    coverFront: z.string(),
    coverBack: z.string().optional(),
    indexPages: z.array(z.string()).optional(),
    available: z.boolean().default(true),
    featured: z.boolean().default(false),
    order: z.number().default(100),
    dimensions: z.object({
      length: z.number(),
      breadth: z.number(),
      height: z.number().optional(),
      pages: z.number().optional(),
      weight: z.number().optional(),
    }).optional(),
  }),
});

export const collections = { books };
