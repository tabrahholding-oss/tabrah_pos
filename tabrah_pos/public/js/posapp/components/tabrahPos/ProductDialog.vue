<template>
  <v-dialog v-model="dialog" max-width="741px" height="720" persistent>
    <v-card style="height: 720px; overflow-y: hidden; border-radius: 16px; display: flex; flex-direction: column;">
      <v-card-title class="d-flex justify-end">
        <v-btn variant="text" size="x-small" density="default" color="white" style="background: orange"
          @click="closeDialog()">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="px-8" style="overflow-y: auto; flex: 1 1 auto;">
        <v-row>
          <!-- Left side: Image and product details -->
          <v-col cols="5">
            <v-img :src="selectedProduct.image" alt="Product Image" height="580 " aspect-ratio="1" cover
              class="mb-4 product-img py-0"></v-img>
            <div class="py-0 item-content">
              <div class="item-name">
                {{ selectedProduct.item_name ? selectedProduct.item_name : "" }}
              </div>
              <div class="item-price" v-if="selectedProduct.custom_discounted_rate > 0"
                style=" text-decoration: line-through!important;color: grey;font-size: 0.9em;margin-right: 5px;">
                QAR.{{
                  selectedProduct.rate ? formatNumber(selectedProduct.rate) : ""
                }}
              </div>
              <div class="item-price" v-else>
                QAR.{{
                  selectedProduct.rate ? formatNumber(selectedProduct.rate) : ""
                }}
              </div>
              <div class="item-price" v-show="selectedProduct.custom_discounted_rate > 0">
                QAR.{{
                  selectedProduct.rate ? formatNumber(selectedProduct.custom_discounted_rate) : ""
                }}
              </div>
            </div>
          </v-col>

          <!-- Right side: Product specifications and actions -->
          <v-col cols="7">
            <div class="d-flex justify-between">
              <div class="black--text item-title">Item Number</div>
              <div>{{ selectedProduct.item_code }}</div>
            </div>

            <div class="mt-3 d-flex justify-between">
              <div class="black--text item-title">Item Detail</div>
              <div>{{ selectedProduct.item_name }}</div>
            </div>
            <div class="mt-4 d-flex justify-between">
              <div class="black--text item-title">Inventory</div>
              <div>{{ selectedProduct.actual_qty }}</div>
            </div>

            <div class="mt-3 d-flex justify-between"></div>

            <div class="d-flex justify-between">
              <!-- <div class="black--text item-title">Embroidery Lawn Dupatta</div>
              <div>2.50 m</div> -->
            </div>

            <div class="d-flex justify-between">
              <!-- <div class="black--text item-title">Died Cambric Trouser</div>
              <div>2.50 m</div> -->
            </div>

            <v-divider class="mt-2 border-opacity-75 mx-6" :thickness="1" style="background-color: grey"></v-divider>

            <!-- Quantity selection and Add to Cart button -->
            <v-row class="my-4 align-center">
              <v-col cols="4" class="text-right">
                <v-btn variant="outlined" size="x-large" class="text-capitalize" color="primary"
                  style="background-color: rgba(var(--v-theme-primary), 0.15); border-radius: 8px" @click="decreaseQuantity">-</v-btn>
              </v-col>
              <v-col cols="4" class="text-center">
                <div class="text-quantity black--text">{{ quantity }}</div>
                <v-divider class="mx-7 border-opacity-75" :thickness="2" style="background-color: black"></v-divider>
              </v-col>
              <v-col cols="4" class="text-left">
                <v-btn variant="outlined" size="x-large" class="text-capitalize" color="primary"
                  style="background-color: rgba(var(--v-theme-primary), 0.15); border-radius: 8px" @click="increaseQuantity">+</v-btn>
              </v-col>
            </v-row>
            <v-row class="my-4 align-center">
              <v-col cols="12" class="text-right">
                <v-text-field
                  class="b-radius-8"
                  variant="outlined"
                  :label="`Discount (max ${pos_profile.posa_max_discount_allowed} %)`"
                  v-model="discount"
                  type="number"
                  :min="0"
                  :max="pos_profile.posa_max_discount_allowed"
                  @input="validateDiscount"
                  :disabled="!pos_profile.posa_max_discount_allowed"
                />
              </v-col>
              <v-col cols="12" class="text-right" v-if="pos_profile.custom_enable_edit_rate_by_group && selectedProduct.item_group === pos_profile.custom_select_item_group_to_edit_rate">
                <v-text-field class="b-radius-8" variant="outlined"
                  label="Rate"
                  v-model="selectedProduct.rate"
                  type="number"
                  :min="0"
                  :disabled="false"
                />
              </v-col>
              <v-col cols="12" class="text-right">
                <v-text-field class="b-radius-8" variant="outlined"
                  :label="`Additional Comment`" v-model="itemComment" 
                  
                   />
              </v-col>
              <v-col cols="12" md="12" class="my-0">
                <v-checkbox v-model="complementaryItem" color="red" label="Complementary Item" @change="handleComplementaryToggle"
                  hide-details></v-checkbox>
              </v-col>
              <v-col cols="12" md="12" class="my-0" v-if="complementaryItem">
                <v-text-field class="b-radius-8" variant="outlined" type="password"
                  label="Enter Pin *" v-model="pin" hide-details="auto"
                  :rules="[v => !!v || 'Pin is required for complementary item']"></v-text-field>
              </v-col>
              <v-col cols="12" md="12" class="my-0" v-if="complementaryItem">
                <v-autocomplete class="b-radius-8" variant="outlined"
                  label="Complimentary Reason *"
                  :items="reasonList"
                  item-title="reason_name"
                  item-value="reason_code"
                  v-model="selectedReason"
                  @update:model-value="onReasonSelect"
                  hide-details="auto"
                  :rules="[v => !!v || 'Reason is required for complementary item']">
                  <template v-slot:item="{ props, item }">
                    <v-list-item v-bind="props"
                      :title="`${item.raw.reason_code} - ${item.raw.reason_name}`"
                      :subtitle="item.raw.description"></v-list-item>
                  </template>
                </v-autocomplete>
              </v-col>

              <!-- <v-col cols="12" md="12" class="my-0">
                <v-checkbox v-model="complementaryLoopy" color="red" label="Loyalty Complementary Item" @change="handleLoopyToggle"
                  hide-details></v-checkbox>
              </v-col> -->
              <!-- <v-col cols="4" class="text-center">
                <div class="text-quantity black--text">{{ quantity }}</div>
                <v-divider
                  class="mx-7 border-opacity-75"
                  :thickness="2"
                  style="background-color: black"
                ></v-divider>
              </v-col>
              <v-col cols="4" class="text-left">
                <v-btn
                  variant="outlined"
                  size="x-large"
                  class="text-capitalize"
                  color="primary"
                  style="background-color: rgba(var(--v-theme-primary), 0.15); border-radius: 8px"
                  @click="increaseQuantity"
                  >+</v-btn
                >
              </v-col> -->
            </v-row>

            <v-row>
              <v-col cols="12">
                <div class="font-weight-bold" style="margin-top: 24px !important">
                  Description
                </div>
                <div class="grey--text">
                  {{ selectedProduct.description }}
                </div>
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-card-text>
      <div style="padding: 24px 32px 24px 32px; background: #fff; box-shadow: 0 -2px 8px rgba(0,0,0,0.03); z-index: 2;">
        <v-btn block size="x-large" color="primary" style="border-radius: 8px" @click="addToCart">
          ADD
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import eventBus from "../../bus";

    const dialog = ref(false);
    const quantity = ref(1); // Initial quantity
    const selectedProduct = ref("");
    const updateQty = ref(false);
    const discount = ref("");
    const pos_profile = ref("");
    const complementaryItem = ref(false);
    const itemComment = ref('')
    const editingIndex = ref(null);
    const pin = ref("");
    const reasonList = ref([]);
    const selectedReason = ref(null);

    const increaseQuantity = () => {
      quantity.value++;
      selectedProduct.value.qty = quantity.value;
    };

    const decreaseQuantity = () => {
      if (quantity.value > 1) {
        quantity.value--;
        selectedProduct.value.qty = quantity.value;
      }
    };
    const formatNumber = (num) => {
      return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(num);
    };

    // Load the list of Complementary Reasons (filtered by company) for the selector
    const loadReasons = () => {
      frappe.call({
        method: "tabrah_pos.tabrah_pos.api.posapp.get_reasons",
        args: { company: pos_profile.value ? pos_profile.value.company : null },
        callback: (r) => {
          reasonList.value = r.message || [];
        },
      });
    };

    // Store selected reason (and its account) on the product
    const onReasonSelect = (val) => {
      selectedProduct.value.custom_complimentary_reason = val || "";
      const reason = reasonList.value.find((x) => x.reason_code === val);
      selectedProduct.value.custom_complimentary_account = reason ? reason.account : "";
    };

    // Verify the entered PIN against the POS Profile employee list (same as OrderSummary)
    const verifyPin = () => {
      const employeeList = pos_profile.value.employee_list || [];
      return employeeList.some((emp) => emp.pin_for_pos === parseInt(pin.value));
    };

    const addToCart = () => {
      // A valid manager/employee PIN is required for complementary items
      if (complementaryItem.value) {
        if (!pin.value) {
          eventBus.emit("show_mesage", {
            text: "Pin is required for complementary item.",
            color: "error",
          });
          return;
        }
        if (!verifyPin()) {
          eventBus.emit("show_mesage", {
            text: "Invalid Pin. Please try again!",
            color: "error",
          });
          return;
        }
        if (!selectedReason.value) {
          eventBus.emit("show_mesage", {
            text: "Reason is required for complementary item.",
            color: "error",
          });
          return;
        }
        // Ensure the reason/account is synced onto the product before emitting
        onReasonSelect(selectedReason.value);
      }
      if (discount.value <= pos_profile.value.posa_max_discount_allowed) {
        // Always sync complementary state before emitting
        selectedProduct.value.complementryItem = Boolean(complementaryItem.value);
        selectedProduct.value.custom_is_complimentary_item = Boolean(complementaryItem.value);
        if(complementaryItem.value)  {
        selectedProduct.value.rate = 0;
        }
        // Do NOT reset rate to original_rate if not complementary; preserve manual edits
        if (!updateQty.value) {
          eventBus.emit("add-to-cart", selectedProduct.value);
        } else {
          selectedProduct.value.index = editingIndex.value;
          eventBus.emit("exist-item-cart", selectedProduct.value);
        }
        complementaryItem.value = false;
        pin.value = "";
        selectedReason.value = null;
        dialog.value = false;
        discount.value = "";
        // Only reset rate if complementary is checked, otherwise preserve manual edits
        if (complementaryItem.value) {
          // selectedProduct.value.rate = selectedProduct.value.original_rate;
        }
      }
    };
    const closeDialog = () => {
      dialog.value = false;
      if (updateQty.value) {
        eventBus.emit("exist-item-cart", selectedProduct.value);
      }
    };
    const validateDiscount = () => {
      if (discount.value === "" || discount.value === null) {
        selectedProduct.value.rate = selectedProduct.value.original_rate;
        return;
      }
      if (discount.value < 0) {
        eventBus.emit("show_mesage", {
          text: `Negative discount is not allowed.`,
          color: "error",
        });
        discount.value = 0;
        selectedProduct.value.rate = selectedProduct.value.original_rate;
        return;
      }
      if (discount.value > pos_profile.value.posa_max_discount_allowed) {
        eventBus.emit("show_mesage", {
          text: `Discount cannot exceed ${pos_profile.value.posa_max_discount_allowed}%`,
          color: "error",
        });
        discount.value = pos_profile.value.posa_max_discount_allowed;
      }
      // Calculate and set the new rate
      const discountAmount =
        (selectedProduct.value.original_rate * discount.value) / 100;
      selectedProduct.value.rate =
        selectedProduct.value.original_rate - discountAmount;
    };

    // Function triggered when checkbox is clicked 
const handleComplementaryToggle = () => {
  if (complementaryItem.value) {
    // Save original rate if not already saved and not zero
    if (!selectedProduct.value.original_rate || selectedProduct.value.original_rate === 0) {
      if (selectedProduct.value.custom_discounted_rate && selectedProduct.value.custom_discounted_rate > 0) {
        selectedProduct.value.original_rate = selectedProduct.value.custom_discounted_rate;
      } else if (selectedProduct.value.rate && selectedProduct.value.rate > 0) {
        selectedProduct.value.original_rate = selectedProduct.value.rate;
      }
    }
    selectedProduct.value.rate = 0;
    selectedProduct.value.complementryItem = true;
    selectedProduct.value.custom_is_complimentary_item = true;
  } else {
    // Only restore rate if original_rate is not zero
    if (selectedProduct.value.original_rate && selectedProduct.value.original_rate > 0) {
      selectedProduct.value.rate = selectedProduct.value.original_rate;
    }
    selectedProduct.value.complementryItem = false;
    selectedProduct.value.custom_is_complimentary_item = false;
    selectedProduct.value.custom_complimentary_reason = "";
    selectedProduct.value.custom_complimentary_account = "";
    pin.value = "";
    selectedReason.value = null;
  }
};

    watch(itemComment, (newVal) => {
      if(newVal){
        selectedProduct.value.comment=newVal
      }
    })
    // watch(complementaryItem, (newValue) => {
    //   if (newValue) {
    //     selectedProduct.value.rate = 0;
    //     selectedProduct.value.complementryItem = true;

    //     console.log("pos_profile", pos_profile.value);
    //     // Filter complementary mode
    //     const complementryMode = pos_profile.value.payments
    //       .filter(profile => profile.custom_is_complementary_mode_of_payment == 1)
    //       .map(profile => ({
    //         ...profile,
    //         amount: selectedProduct.value.original_rate // Add original amount
    //       }));

    //     console.log("complementryMode", complementryMode);
    //   } else {
    //     selectedProduct.value.rate = selectedProduct.value.original_rate;
    //     selectedProduct.value.complementryItem = false;

    //     // Reset the filtered complementary mode with zero amount
    //     const complementryMode = pos_profile.value.payments
    //       .filter(profile => profile.custom_is_complementary_mode_of_payment == 1)
    //       .map(profile => ({
    //         ...profile,
    //         amount: 0 // Set amount to zero
    //       }));

    //     console.log("complementryMode", complementryMode);
    //   }
    // });

    onMounted(() => {
      eventBus.on("open-product-dialog", (data) => {
        loadReasons();
        editingIndex.value = data.index ?? null;
        updateQty.value = data.flag;
        quantity.value = data.product.qty ? data.product.qty : 1;
        data.product.qty = quantity.value;
        selectedProduct.value = JSON.parse(JSON.stringify(data.product));
        itemComment.value = data.product.comment || '';
        complementaryItem.value = Boolean(data.product.complementryItem);
        pin.value = "";
        selectedReason.value = data.product.custom_complimentary_reason || null;

        // If not complementary, and original_rate is missing or zero, but rate is also zero, try to recover
        if (!complementaryItem.value) {
          if (!selectedProduct.value.original_rate || selectedProduct.value.original_rate === 0) {
            // Try to recover from custom_discounted_rate if available and > 0
            if (selectedProduct.value.custom_discounted_rate && selectedProduct.value.custom_discounted_rate > 0) {
              selectedProduct.value.original_rate = selectedProduct.value.custom_discounted_rate;
              if (selectedProduct.value.rate === 0) {
                selectedProduct.value.rate = selectedProduct.value.custom_discounted_rate;
              }
            } else if (selectedProduct.value.rate && selectedProduct.value.rate > 0) {
              selectedProduct.value.original_rate = selectedProduct.value.rate;
            }
          }
        }

        // If complementary, always set rate to 0, but do not overwrite original_rate if already set and not zero
        if (complementaryItem.value) {
          if (!selectedProduct.value.original_rate || selectedProduct.value.original_rate === 0) {
            // Try to recover original_rate from custom_discounted_rate or previous rate
            if (selectedProduct.value.custom_discounted_rate && selectedProduct.value.custom_discounted_rate > 0) {
              selectedProduct.value.original_rate = selectedProduct.value.custom_discounted_rate;
            } else if (selectedProduct.value.rate && selectedProduct.value.rate > 0) {
              selectedProduct.value.original_rate = selectedProduct.value.rate;
            }
          }
          selectedProduct.value.rate = 0;
        }
        if (selectedProduct.value) {
          dialog.value = true;
        }

      });

      eventBus.on("send_pos_profile", async (profile) => {
        console.log("pos-profile", profile);
        pos_profile.value = profile;
      });
    });


</script>

<style scoped>
.text-h5 {
  font-size: 24px;
}

.text-h6 {
  font-size: 20px;
}

.grey--text {
  color: #9e9e9e;
}

.product-img {
  /* height: 537px; */
  position: relative;
  bottom: 81px;
}

.item-content {
  position: relative;
  bottom: 60px;
}

.item-name {
  font-size: 16px;
  font-weight: 800;
}

.item-price {
  font-size: 14px;
  font-weight: 700;
  color: #f69e7b;
}

.item-title {
  font-size: 12px;
  font-weight: 700;
}

.text-quantity {
  font-size: 35px;
  font-weight: 500;
}
</style>
